"""Run many dealt games and judge the numbers against the balance bar."""
import statistics
from dataclasses import dataclass

from inn_sim.deal import deal_run
from inn_sim.params import DEFAULT_PARAMS
from inn_sim.players import CarefulPlayer, RandomPlayer
from inn_sim.rules import RunResult, play_run

Params = dict[str, float]

# The balance bar, from the spec.
CAREFUL_WIN = (0.70, 0.80)
CAREFUL_MARGIN = (0.0, 0.15)
RANDOM_WIN_BELOW = 0.20
SENSITIVITY_BAND = (0.60, 0.90)
SENSITIVITY_SKIP = {"days", "travelers_min", "travelers_max"}
PROBABILITIES = {"thief_p", "hint_accuracy", "hint_false_pos", "cheap_discount"} | {
    name for name in DEFAULT_PARAMS if name.startswith("p_") or name.endswith("_frac")}


@dataclass(frozen=True)
class Stats:
    runs: int
    win_rate: float
    median_end: float
    median_margin: float  # (median_end - debt) / debt


def play_pairs(params: Params, runs: int, seed: int) -> list[tuple[int, RunResult, RunResult]]:
    """Both players face the same deal for each run."""
    out = []
    for i in range(runs):
        deal = deal_run(params, seed + i)
        out.append((seed + i, play_run(params, deal, CarefulPlayer()), play_run(params, deal, RandomPlayer(seed + i))))
    return out


def _stats(results: list[RunResult], debt: float) -> Stats:
    median_end = statistics.median(r.end_coins for r in results)
    return Stats(len(results), sum(r.won for r in results) / len(results), median_end, (median_end - debt) / debt)


def simulate(params: Params, runs: int, seed: int) -> dict[str, Stats]:
    pairs = play_pairs(params, runs, seed)
    return {
        "careful": _stats([c for _, c, _ in pairs], params["debt"]),
        "random": _stats([r for _, _, r in pairs], params["debt"]),
    }


def check_bar(stats: dict[str, Stats]) -> list[str]:
    careful, rand = stats["careful"], stats["random"]
    problems = []
    if not CAREFUL_WIN[0] <= careful.win_rate <= CAREFUL_WIN[1]:
        problems.append(f"careful win rate {careful.win_rate:.3f} outside {CAREFUL_WIN[0]:.2f}-{CAREFUL_WIN[1]:.2f}")
    if not CAREFUL_MARGIN[0] <= careful.median_margin <= CAREFUL_MARGIN[1]:
        problems.append(f"careful median margin {careful.median_margin:+.1%} outside "
                        f"{CAREFUL_MARGIN[0]:.0%}-{CAREFUL_MARGIN[1]:.0%}")
    if not rand.win_rate < RANDOM_WIN_BELOW:
        problems.append(f"random win rate {rand.win_rate:.3f} not below {RANDOM_WIN_BELOW:.2f}")
    return problems


def _nudge(name: str, value: float, factor: float) -> float:
    if isinstance(DEFAULT_PARAMS[name][0], int):
        # Whole numbers must actually move, or small values like upkeep 3 never get tested.
        new = round(value * factor)
        if new == value:
            new = value + (1 if factor > 1 else -1)
    else:
        new = value * factor
    if name in PROBABILITIES:
        new = min(1.0, new)
    return max(0.0, float(new))


def sensitivity(params: Params, runs: int, seed: int) -> list[tuple[str, float, float]]:
    """Each param x0.9 and x1.1 alone; report the nudges that push the careful win rate out of the band."""
    flagged = []
    for name in params:
        if name in SENSITIVITY_SKIP:
            continue
        for factor in (0.9, 1.1):
            new = _nudge(name, params[name], factor)
            if new == params[name]:
                continue
            win = simulate({**params, name: new}, runs, seed)["careful"].win_rate
            if not SENSITIVITY_BAND[0] <= win <= SENSITIVITY_BAND[1]:
                flagged.append((name, factor, win))
    return flagged
