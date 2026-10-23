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
    header_at = next((i for i in range(seed_at + 1, len(rows)) if "day" in rows[i] and "decision" in rows[i]), None)
    header = rows[header_at] if header_at is not None else []
    col = {name: header.index(name) for name in HANDPLAY_HEADER if name in header}
    missing = [name for name in ("day", "slot", "kind_shown", "decision") if name not in col]
    if missing:
        raise ValueError(f"HandPlay header row is missing column(s): {', '.join(missing)}")

    def cell(row: list[str], name: str) -> str:
        i = col.get(name)
        return row[i].strip() if i is not None and i < len(row) else ""

    market: dict[int, tuple[int, int]] = {}
    decisions: dict[tuple[int, int], Action] = {}
    sheet_rows: dict[tuple[int, int], int] = {}
    already_warned: set[tuple[int, int]] = set()
    warnings: list[str] = []
    for i in range(header_at + 1, len(rows)):
        row, sheet_row = rows[i], i + 1
        if not row or not cell(row, "day"):
            continue
        try:
            day, slot = _int(cell(row, "day")), _int(cell(row, "slot"))
        except ValueError:
            warnings.append(f"row {sheet_row}: day/slot not a number; row ignored")
            continue
        sheet_rows[(day, slot)] = sheet_row
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
            already_warned.add((day, slot))
        elif action.startswith("haggle") and cell(row, "kind_shown") != "noble":
            warnings.append(f"row {sheet_row}: {action} is only for nobles, not {cell(row, 'kind_shown')}; "
                            "treated as decline")
            already_warned.add((day, slot))
        else:
            decisions[(day, slot)] = action  # type: ignore[assignment]
    player = ScriptedPlayer(market, decisions)
    player.sheet_rows = sheet_rows
    player.already_warned = already_warned
    return seed, player, warnings


def blank_decision_warnings(player: ScriptedPlayer) -> list[str]:
    """After a replay: travelers who really arrived but had a blank decision cell."""
    return [f"row {player.sheet_rows.get(key, '?')}: no decision for day {key[0]} slot {key[1]}; "
            "treated as decline" for key in player.defaulted if key not in player.already_warned]


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


# --- daily mode: one day at a time ---
# Same columns, but the arrivals column holds the real count, which is known each morning.
DAILY_HEADER = ["arrivals" if name == "base_arrivals" else name for name in HANDPLAY_HEADER]
_DAILY_MARK = "mode=daily"


def is_daily(rows: list[list[str]]) -> bool:
    return any(len(r) > 1 and r[0].strip().startswith("seed=") and r[1].strip() == _DAILY_MARK for r in rows)


def last_dealt_day(rows: list[list[str]]) -> int:
    days = []
    for r in rows:
        try:
            days.append(_int(r[0]))
        except (ValueError, IndexError):
            continue
    return max(days, default=0)


def _user_cells(rows: list[list[str]]) -> dict[tuple[int, int], dict[str, str]]:
    """The cells the player filled in, keyed by (day, slot)."""
    header_at = next((i for i, r in enumerate(rows) if "day" in r and "decision" in r), None)
    if header_at is None:
        return {}
    col = {name: rows[header_at].index(name) for name in _USER_COLUMNS if name in rows[header_at]}
    day_i, slot_i = rows[header_at].index("day"), rows[header_at].index("slot")
    cells: dict[tuple[int, int], dict[str, str]] = {}
    for r in rows[header_at + 1:]:
        try:
            key = (_int(r[day_i]), _int(r[slot_i]))
        except (ValueError, IndexError):
            continue
        cells[key] = {name: r[i] for name, i in col.items() if i < len(r) and r[i].strip()}
    return cells


def daily_rows(deal: RunDeal, params: dict[str, float], arrivals: dict[int, int],
               user_rows: list[list[str]] | None = None) -> list[list]:
    """HandPlay for days 1..max(arrivals): only travelers who really arrived, with the player's cells kept."""
    kept = _user_cells(user_rows or [])
    rows: list[list] = [[f"seed={deal.seed}", _DAILY_MARK], list(DAILY_HEADER)]
    for day in deal.days[:max(arrivals, default=0)]:
        for slot, t in enumerate(day.travelers[:arrivals.get(day.day, 0)], start=1):
            row = [day.day, day.weather, day.price_food, day.price_firewood, arrivals[day.day], slot,
                   t.kind, "yes" if t.hint else "no", _needs(t.kind), _base_offer(t.kind, params), "", "", "", ""]
            for name, value in kept.get((day.day, slot), {}).items():
                if name.startswith("buy_"):
                    try:
                        value = float(value)  # keep amounts as numbers in Calc
                    except ValueError:
                        pass  # read_decisions will warn about it
                row[HANDPLAY_HEADER.index(name)] = value
            rows.append(row)
    return rows
