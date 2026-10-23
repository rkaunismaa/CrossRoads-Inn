"""Command line: python3 -m inn_sim <command>. Run from prototype/."""
import argparse
import csv
import sys
from pathlib import Path

from inn_sim import report
from inn_sim.params import load_params, params_from_defaults


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
    flagged = report.sensitivity(_params(args.ods), args.runs, args.seed)
    if not flagged:
        print("SENSITIVITY: PASS")
        return 0
    print("SENSITIVITY: FAIL")
    for name, factor, win in flagged:
        print(f"  - {name} x{factor}: careful win {win:.3f}")
    return 1


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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
