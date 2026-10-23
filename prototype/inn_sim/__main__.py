"""Command line: python3 -m inn_sim <command>. Run from prototype/."""
import argparse
import csv
import sys
from pathlib import Path

from inn_sim import report
from inn_sim.params import ParamError, WorkbookLocked, load_params, params_from_defaults


def _params(ods: str) -> dict[str, float]:
    path = Path(ods)
    if not path.exists():
        print(f"warning: {path} not found, using DEFAULT_PARAMS", file=sys.stderr)
        return params_from_defaults()
    return load_params(path)


def _print_stats(stats: dict[str, report.Stats]) -> None:
    for name, s in stats.items():
        print(f"{name:8} runs={s.runs} win={s.win_rate:.3f} median_end={s.median_end:g} "
              f"margin={s.median_margin:+.1%}")


def cmd_simulate(args: argparse.Namespace) -> int:
    params = _params(args.ods)
    stats = report.simulate(params, args.runs, args.seed)
    _print_stats(stats)
    problems = report.check_bar(stats)
    print("BAR: PASS" if not problems else "BAR: FAIL")
    for p in problems:
        print(f"  - {p}")
    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["seed", "careful_won", "careful_end", "careful_lost_day",
                        "random_won", "random_end", "random_lost_day"])
            for seed, c, r in report.play_pairs(params, args.runs, args.seed):
                w.writerow([seed, int(c.won), c.end_coins, c.lost_on_day or "",
                            int(r.won), r.end_coins, r.lost_on_day or ""])
    return 0 if not problems else 1


def cmd_sensitivity(args: argparse.Namespace) -> int:
    params = _params(args.ods)
    flagged = report.sensitivity(params, args.runs, args.seed)
    untested = report.untested_params(params)
    if untested:
        print(f"not tested (whole numbers too small to move by 10%): {', '.join(untested)}")
    if not flagged:
        print("SENSITIVITY: PASS")
        return 0
    print("SENSITIVITY: FAIL")
    for name, factor, win in flagged:
        print(f"  - {name} x{factor}: careful win {win:.3f}")
    return 1


def cmd_init(args: argparse.Namespace) -> int:
    from inn_sim.ods_write import create_workbook

    create_workbook(Path(args.ods))
    print(f"created {args.ods} with Params, HandPlay and Reveal sheets")
    return 0


def cmd_deal(args: argparse.Namespace) -> int:
    from inn_sim.deal import deal_run
    from inn_sim.handplay import REVEAL_HEADER, daily_rows, deal_to_rows, reveal_rows
    from inn_sim.ods_write import write_sheets
    from inn_sim.rules import arrivals, new_state

    params = load_params(Path(args.ods))
    deal = deal_run(params, args.seed)
    if args.daily:
        first = arrivals(new_state(params), deal.days[0], params)
        write_sheets(Path(args.ods), {"HandPlay": daily_rows(deal, params, {1: first}),
                                      "Reveal": [REVEAL_HEADER], "DayLog": [["Day log: filled in by next"]]})
        print(f"dealt day 1 of seed {args.seed} into {args.ods}: fill buy_food/buy_firewood (slot 1 row) and "
              "decision, save, close Calc, then run: python3 -m inn_sim next")
        return 0
    write_sheets(Path(args.ods), {"HandPlay": deal_to_rows(deal, params), "Reveal": reveal_rows(deal)})
    print(f"dealt seed {args.seed} into {args.ods}: fill buy_food/buy_firewood (slot 1 rows) and decision, "
          "save, close Calc, then run: python3 -m inn_sim replay")
    return 0


def _print_results(params: dict[str, float], yours: object, careful: object) -> None:
    print("--- result ---")
    for name, r in (("you", yours), ("careful", careful)):
        lost = f", lost on day {r.lost_on_day}" if r.lost_on_day else ""
        print(f"{name:8} {'WIN ' if r.won else 'LOSS'} end coins {r.end_coins} (debt {int(params['debt'])}){lost}")


def cmd_next(args: argparse.Namespace) -> int:
    from inn_sim.deal import deal_run
    from inn_sim.handplay import (blank_decision_warnings, daily_rows, is_daily, last_dealt_day, read_decisions,
                                  reveal_rows)
    from inn_sim.ods_write import write_sheets
    from inn_sim.params import read_sheet
    from inn_sim.players import CarefulPlayer
    from inn_sim.rules import arrivals, play_days, play_run

    ods = Path(args.ods)
    params = load_params(ods)
    rows = read_sheet(ods, "HandPlay")
    if not is_daily(rows):
        raise ValueError("HandPlay is not a daily run; start one with: python3 -m inn_sim deal --seed N --daily")
    if any(r and r[0] == "final_event" for r in read_sheet(ods, "Reveal")):
        raise ValueError("this run is over; deal a new one with: python3 -m inn_sim deal --seed N --daily")

    seed, player, warnings = read_decisions(rows)
    deal = deal_run(params, seed)
    today, last_day = last_dealt_day(rows), int(params["days"])
    progress = play_days(params, deal, player, today)
    for w in warnings + blank_decision_warnings(player):
        print(f"warning: {w}")

    # How today turned out comes first.
    print(f"--- how day {today} went ---")
    print("\n".join(line for line in progress.ledger if line.split(":")[0].split(" ")[1] == str(today)))

    finished = progress.lost_on_day is not None or today == last_day
    if not finished and progress.state.coins < params["upkeep"]:
        print(f"Day {today + 1}: could not pay upkeep, run lost")
        finished = True
    if finished:
        _, player, _ = read_decisions(rows)  # fresh player for the full replay
        yours = play_run(params, deal, player)
        _print_results(params, yours, play_run(params, deal, CarefulPlayer()))
        write_sheets(ods, {"DayLog": [[line] for line in yours.ledger], "Reveal": reveal_rows(deal)})
        print("the Reveal sheet now shows the hidden truth of this run")
        return 0

    tomorrow = today + 1
    counts = {**progress.arrivals, tomorrow: arrivals(progress.state, deal.days[today], params)}
    write_sheets(ods, {"HandPlay": daily_rows(deal, params, counts, user_rows=rows),
                       "DayLog": [[line] for line in progress.ledger]})
    print(f"--- Day {tomorrow} is dealt: {counts[tomorrow]} travelers. Fill it in, save, close Calc, "
          "then run next again ---")
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    from inn_sim.deal import deal_run
    from inn_sim.handplay import blank_decision_warnings, dealt_columns_match, read_decisions
    from inn_sim.params import read_sheet
    from inn_sim.players import CarefulPlayer
    from inn_sim.rules import play_run

    params = load_params(Path(args.ods))
    rows = read_sheet(Path(args.ods), "HandPlay")
    seed, player, warnings = read_decisions(rows)
    deal = deal_run(params, seed)
    if not dealt_columns_match(rows, deal, params):
        print("warning: Params changed since this run was dealt; the replay uses the current Params")
    for w in warnings:
        print(f"warning: {w}")
    yours = play_run(params, deal, player)
    for w in blank_decision_warnings(player):
        print(f"warning: {w}")
    careful = play_run(params, deal, CarefulPlayer())
    print(f"--- your run (seed {seed}) ---")
    print("\n".join(yours.ledger))
    _print_results(params, yours, careful)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inn_sim", description="Crossroads Inn paper-prototype simulation")
    sub = parser.add_subparsers(dest="command", required=True)

    sim = sub.add_parser("simulate", help="careful vs random over many runs, judged against the bar")
    sim.add_argument("--ods", default="balance.ods")
    sim.add_argument("--runs", type=int, default=5000)
    sim.add_argument("--seed", type=int, default=0)
    sim.add_argument("--csv", help="also write per-run results to this CSV file")
    sim.set_defaults(func=cmd_simulate)

    sens = sub.add_parser("sensitivity", help="nudge each param by +/-10%% and flag ones that break the band")
    sens.add_argument("--ods", default="balance.ods")
    sens.add_argument("--runs", type=int, default=2000)
    sens.add_argument("--seed", type=int, default=0)
    sens.set_defaults(func=cmd_sensitivity)

    init = sub.add_parser("init", help="create balance.ods from DEFAULT_PARAMS (never overwrites)")
    init.add_argument("--ods", default="balance.ods")
    init.set_defaults(func=cmd_init)

    deal = sub.add_parser("deal", help="deal a seeded run into the HandPlay and Reveal sheets")
    deal.add_argument("--ods", default="balance.ods")
    deal.add_argument("--seed", type=int, required=True)
    deal.add_argument("--daily", action="store_true", help="deal only day 1; use next to go day by day")
    deal.set_defaults(func=cmd_deal)

    replay = sub.add_parser("replay", help="replay your HandPlay decisions and compare with the careful player")
    replay.add_argument("--ods", default="balance.ods")
    replay.set_defaults(func=cmd_replay)

    nxt = sub.add_parser("next", help="daily mode: show how today went, then deal the next day")
    nxt.add_argument("--ods", default="balance.ods")
    nxt.set_defaults(func=cmd_next)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ParamError, WorkbookLocked, FileExistsError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
