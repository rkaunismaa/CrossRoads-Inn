"""Export the tuned numbers and dealt test runs for the Godot game."""
import json
from pathlib import Path

from inn_sim.params import DEFAULT_PARAMS
from inn_sim.report import WHOLE_PARAMS

_ALSO_WHOLE = {"days", "travelers_min", "travelers_max"}


def params_for_export(params: dict[str, float]) -> dict[str, int | float]:
    """Params in DEFAULT_PARAMS order; whole-number params as ints so GDScript gets clean values."""
    out: dict[str, int | float] = {}
    for name in DEFAULT_PARAMS:
        value = params[name]
        out[name] = int(value) if name in WHOLE_PARAMS | _ALSO_WHOLE else float(value)
    return out


def export_params(params: dict[str, float], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(params_for_export(params), indent=2) + "\n")


# --- parity fixtures for the GDScript rules ---
import hashlib  # noqa: E402
from dataclasses import asdict  # noqa: E402

from inn_sim.deal import deal_run  # noqa: E402
from inn_sim.model import DayDeal, DealtTraveler, RunDeal  # noqa: E402
from inn_sim.players import CarefulPlayer, RandomPlayer, RecordingPlayer  # noqa: E402
from inn_sim.rules import play_run  # noqa: E402

# Every one of these must appear in some fixture's ledger, so each rule branch is checked in Godot.
REQUIRED_MARKERS = ("walked out", "thief stole", "short ", "could not pay upkeep", "blizzard", "hungry soldiers",
                    "robbery took", "robbery stopped", "declined (no room)", "declined (no food)",
                    "declined (can't haggle)", "news:", "WIN")


class _AcceptAll:
    """Accepts everyone and buys nothing: runs out of rooms and food, reaching the decline branches."""

    def market(self, state, day, params):
        return (0, 0)

    def decide(self, state, day, slot, view, params):
        return "accept"


class _HaggleHigh(_AcceptAll):
    """Asks every traveler for the noble's top price: walk-outs and can't-haggle declines."""

    def decide(self, state, day, slot, view, params):
        return "haggle_high"


def params_hash(params: dict[str, float]) -> str:
    return hashlib.sha256(json.dumps(params_for_export(params), sort_keys=True).encode()).hexdigest()


def deal_from_dict(d: dict) -> RunDeal:
    days = tuple(DayDeal(**{**day, "travelers": tuple(DealtTraveler(**t) for t in day["travelers"])})
                 for day in d["days"])
    return RunDeal(d["seed"], days, d["final_event"])


def fixture_dict(name: str, params: dict[str, float], deal: RunDeal, player: RecordingPlayer) -> dict:
    result = play_run(params, deal, player)
    return {
        "name": name,
        "params": params_for_export(params),
        "deal": asdict(deal),
        "market": {str(day): list(buys) for day, buys in sorted(player.market_buys.items())},
        "decisions": [[day, slot, action] for (day, slot), action in sorted(player.decisions.items())],
        "ledger": list(result.ledger),
        "result": {"won": result.won, "end_coins": result.end_coins, "lost_on_day": result.lost_on_day},
    }


def _fixture_set(params: dict[str, float]) -> list[dict]:
    makers = ([(f"careful_{s}", s, CarefulPlayer) for s in range(8)]
              + [(f"random_{s}", s, lambda s=s: RandomPlayer(s)) for s in range(6)]
              + [(f"accept_all_{s}", s, _AcceptAll) for s in range(3)]
              + [(f"haggle_high_{s}", s, _HaggleHigh) for s in range(3)])
    fixtures = [fixture_dict(name, params, deal_run(params, seed), RecordingPlayer(make()))
                for name, seed, make in makers]

    def missing() -> list[str]:
        text = "\n".join(line for f in fixtures for line in f["ledger"])
        return [m for m in REQUIRED_MARKERS if m not in text]

    # Top up with more seeds until every rule branch shows up somewhere.
    for seed in range(8, 500):
        if not missing():
            break
        for name, make in ((f"careful_{seed}", CarefulPlayer), (f"random_{seed}", lambda: RandomPlayer(seed))):
            f = fixture_dict(name, params, deal_run(params, seed), RecordingPlayer(make()))
            if any(m in "\n".join(f["ledger"]) for m in missing()):
                fixtures.append(f)
    if missing():
        raise ValueError(f"no fixture covers: {', '.join(missing())}")
    return fixtures


def export_fixtures(params: dict[str, float], out_dir: Path) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.json"):
        old.unlink()
    names = []
    for f in _fixture_set(params):
        name = f"{f['name']}.json"
        (out_dir / name).write_text(json.dumps(f, indent=1) + "\n")
        names.append(name)
    manifest = {"params_hash": params_hash(params), "files": names,
                "regenerate": "cd prototype && python3 -m inn_sim export-fixtures"}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    return names
