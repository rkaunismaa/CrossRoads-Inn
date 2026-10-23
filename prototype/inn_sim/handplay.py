"""Hand play: deal a seeded run into the workbook, and read the user's decisions back."""

HANDPLAY_HEADER = ["day", "weather", "price_food", "price_firewood", "base_arrivals", "slot", "kind_shown",
                   "hint", "needs", "base_offer", "buy_food", "buy_firewood", "decision", "notes"]
REVEAL_HEADER = ["day", "slot", "true_kind", "is_thief", "noble_tier", "news"]

from inn_sim.model import ACTIONS, Action, RunDeal
from inn_sim.players import ScriptedPlayer
from inn_sim.rules import NEEDS

_USER_COLUMNS = ("buy_food", "buy_firewood", "decision", "notes")


def _base_offer(kind: str, params: dict[str, float]) -> int:
    if kind == "noble":
        return int(params["noble_offer"])
    if kind == "wanderer":
        return 0
    return int(params[f"pay_{kind}"])


def _needs(kind: str) -> str:
    room, meal = NEEDS[kind]
    return "+".join(n for n, wanted in (("room", room), ("meal", meal)) if wanted)


def deal_to_rows(deal: RunDeal, params: dict[str, float]) -> list[list]:
    """The HandPlay sheet: everything a player may see, nothing hidden."""
    rows: list[list] = [[f"seed={deal.seed}"], list(HANDPLAY_HEADER)]
    for day in deal.days:
        for slot, t in enumerate(day.travelers, start=1):
            rows.append([day.day, day.weather, day.price_food, day.price_firewood, day.base_arrivals, slot,
                         t.kind, "yes" if t.hint else "no", _needs(t.kind), _base_offer(t.kind, params),
                         "", "", "", ""])
    return rows


def reveal_rows(deal: RunDeal) -> list[list]:
    """The Reveal sheet: the hidden truth, to look at after deciding."""
    rows: list[list] = [list(REVEAL_HEADER)]
    for day in deal.days:
        for slot, t in enumerate(day.travelers, start=1):
            rows.append([day.day, slot, "thief" if t.is_thief else t.kind, "yes" if t.is_thief else "no",
                         t.noble_tier if t.kind == "noble" else "", t.news or ""])
    rows.append(["final_event", deal.final_event])
    return rows


def _int(text: str) -> int:
    return int(float(text))


def read_decisions(rows: list[list[str]]) -> tuple[int, ScriptedPlayer, list[str]]:
    """Turn the filled-in HandPlay sheet into (seed, player, warnings). Bad cells become warnings, not crashes."""
    seed_at = next((i for i, r in enumerate(rows) if r and r[0].strip().startswith("seed=")), None)
    if seed_at is None:
        raise ValueError("HandPlay sheet has no seed=<n> row; deal a run first")
    seed = _int(rows[seed_at][0].split("=", 1)[1])
    header = rows[seed_at + 1]
    col = {name: header.index(name) for name in HANDPLAY_HEADER if name in header}

    def cell(row: list[str], name: str) -> str:
        i = col.get(name)
        return row[i].strip() if i is not None and i < len(row) else ""

    market: dict[int, tuple[int, int]] = {}
    decisions: dict[tuple[int, int], Action] = {}
    warnings: list[str] = []
    for i in range(seed_at + 2, len(rows)):
        row, sheet_row = rows[i], i + 1
        if not row or not cell(row, "day"):
            continue
        try:
            day, slot = _int(cell(row, "day")), _int(cell(row, "slot"))
        except ValueError:
            warnings.append(f"row {sheet_row}: day/slot not a number; row ignored")
            continue
        for name in ("buy_food", "buy_firewood"):
            raw = cell(row, name)
            if not raw:
                continue
            try:
                amount = _int(raw)
            except ValueError:
                warnings.append(f"row {sheet_row}: {name} {raw!r} is not a number; treated as 0")
                continue
            food, wood = market.get(day, (0, 0))
            market[day] = (amount, wood) if name == "buy_food" else (food, amount)
        raw = cell(row, "decision")
        action = raw.lower()
        if not action:
            continue
        if action not in ACTIONS:
            warnings.append(f"row {sheet_row}: unknown decision {raw!r}; treated as decline")
        elif action.startswith("haggle") and cell(row, "kind_shown") != "noble":
            warnings.append(f"row {sheet_row}: {action} is only for nobles, not {cell(row, 'kind_shown')}; "
                            "treated as decline")
        else:
            decisions[(day, slot)] = action  # type: ignore[assignment]
    return seed, ScriptedPlayer(market, decisions), warnings


def dealt_columns_match(rows: list[list[str]], deal: RunDeal, params: dict[str, float]) -> bool:
    """True if the sheet's dealt columns still match a fresh deal (Params unchanged since dealing)."""
    expected = deal_to_rows(deal, params)[2:]
    seed_at = next(i for i, r in enumerate(rows) if r and r[0].strip().startswith("seed="))
    sheet = rows[seed_at + 2:]
    keep = [i for i, name in enumerate(HANDPLAY_HEADER) if name not in _USER_COLUMNS]
    if len(sheet) != len(expected):
        return False
    for got, want in zip(sheet, expected):
        got = got + [""] * (len(HANDPLAY_HEADER) - len(got))
        for i in keep:
            w = want[i]
            if got[i].strip() != (str(w) if not isinstance(w, float) else f"{w:g}"):
                return False
    return True
