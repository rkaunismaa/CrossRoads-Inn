"""Tunable numbers and reading them from the Params sheet of balance.ods.

DEFAULT_PARAMS is only used to create the workbook the first time and as a
test fixture. Once balance.ods exists, its Params sheet is the source of truth.
"""
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

DEFAULT_PARAMS: dict[str, tuple[float, str]] = {
    # Start and run
    "start_coins": (20, "Coins at the start of day 1"),
    "start_food": (10, "Food at the start of day 1"),
    "start_firewood": (8, "Firewood at the start of day 1"),
    "start_goodwill": (0, "Hidden goodwill at the start"),
    "days": (7, "Length of a run in days"),
    "debt": (60, "Landlord debt due after day 7; this is the coin target"),
    "upkeep": (3, "Coins paid each morning; failing to pay loses the run"),
    "rooms": (3, "Rooms available each night"),
    # Market
    "price_food": (2, "Base market price of one food"),
    "price_firewood": (2, "Base market price of one firewood"),
    "price_jitter": (0.25, "Daily price varies by +/- this fraction"),
    "p_cheap_day": (0.15, "Chance a day is a cheap firewood day"),
    "cheap_discount": (0.5, "Firewood price multiplier on a cheap day"),
    # Weather and fire
    "p_cold": (0.3, "Chance a day is cold"),
    "p_snow": (0.15, "Chance a day is snowy"),
    "fire_base": (1, "Firewood burned each night with no guests"),
    "fire_per_room": (1, "Extra firewood per occupied room"),
    "mult_cold": (1.5, "Firewood multiplier on a cold night"),
    "mult_snow": (2.0, "Firewood multiplier on a snowy night"),
    "blizzard_mult": (2.0, "Extra firewood multiplier for the final-night blizzard"),
    "shortage_coin_per_unit": (2, "Coins lost per missing firewood"),
    "shortage_goodwill": (1, "Goodwill lost on a night with too little firewood"),
    # Arrivals and traveler types
    "travelers_min": (3, "Fewest base arrivals per day"),
    "travelers_max": (5, "Most base arrivals per day"),
    "goodwill_arrival_threshold": (5, "Goodwill at or above this brings one extra traveler"),
    "w_merchant": (3, "Weight of merchants (some are thieves)"),
    "w_pilgrim": (2, "Weight of pilgrims"),
    "w_soldier": (2, "Weight of soldiers"),
    "w_noble": (1, "Weight of nobles"),
    "w_wanderer": (1, "Weight of wanderers"),
    "thief_p": (0.3, "Chance a merchant is really a thief"),
    # Payment and needs
    "pay_merchant": (8, "Merchant pay for room and meal"),
    "pay_pilgrim": (1, "Pilgrim pay for a meal"),
    "pilgrim_goodwill": (1, "Goodwill gained by feeding a pilgrim"),
    "pay_soldier": (6, "Soldier pay for a room"),
    "food_per_meal": (1, "Food used by one meal"),
    "goodwill_pay_bonus": (0.05, "Pay multiplier gained per point of goodwill"),
    "goodwill_cap": (10, "Highest goodwill can go"),
    # Thief
    "hint_accuracy": (0.7, "Chance Bram hints when the merchant is a thief"),
    "hint_false_pos": (0.2, "Chance Bram hints when the merchant is honest"),
    "thief_steal_frac": (0.3, "Fraction of coins a thief takes at night"),
    # Noble
    "noble_offer": (6, "Noble's opening offer for a room"),
    "noble_mid": (10, "Price asked with haggle_mid"),
    "noble_high": (15, "Price asked with haggle_high"),
    "p_noble_mid": (0.6, "Chance the noble accepts at least haggle_mid"),
    "p_noble_high": (0.3, "Chance the noble accepts haggle_high"),
    "walkout_goodwill_loss": (2, "Goodwill lost when the noble walks out"),
    # Final night
    "hungry_soldiers_food": (6, "Food the hungry soldiers eat on night 7"),
    "final_food_penalty": (3, "Coins lost per food short for the hungry soldiers"),
    "robbery_frac": (0.4, "Fraction of coins taken by the robbery"),
    "robbery_safe_goodwill": (4, "Goodwill at or above this stops the robbery"),
}

_NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
}
_MAX_REPEAT = 1000


class ParamError(ValueError):
    """A problem with the workbook or its Params sheet."""


class WorkbookLocked(RuntimeError):
    """The workbook is open in Calc (its lock file exists)."""


def params_from_defaults() -> dict[str, float]:
    return {name: float(value) for name, (value, _note) in DEFAULT_PARAMS.items()}


def _attr(el: ET.Element, ns: str, name: str) -> str | None:
    return el.get(f"{{{_NS[ns]}}}{name}")


def _cell_text(cell: ET.Element) -> str:
    # Numeric cells carry their exact value in office:value; prefer it over the
    # displayed text, which depends on the user's number format and locale.
    value = _attr(cell, "office", "value")
    if value is not None:
        return value
    return "\n".join("".join(p.itertext()) for p in cell.findall("text:p", _NS))


def _trim(values: list[str]) -> list[str]:
    while values and values[-1] == "":
        values.pop()
    return values


def read_sheet(ods_path: Path, sheet: str) -> list[list[str]]:
    try:
        with zipfile.ZipFile(ods_path) as z:
            root = ET.fromstring(z.read("content.xml"))
    except (OSError, KeyError, zipfile.BadZipFile) as e:
        raise ParamError(f"cannot read {ods_path}: {e}") from e
    for table in root.iter(f"{{{_NS['table']}}}table"):
        if _attr(table, "table", "name") != sheet:
            continue
        rows: list[list[str]] = []
        for row in table.iter(f"{{{_NS['table']}}}table-row"):
            values: list[str] = []
            for cell in row:
                if cell.tag not in (f"{{{_NS['table']}}}table-cell", f"{{{_NS['table']}}}covered-table-cell"):
                    continue
                repeat = min(int(_attr(cell, "table", "number-columns-repeated") or 1), _MAX_REPEAT)
                values.extend([_cell_text(cell)] * repeat)
            values = _trim(values)
            repeat = min(int(_attr(row, "table", "number-rows-repeated") or 1), _MAX_REPEAT)
            rows.extend([list(values) for _ in range(repeat)])
        while rows and not rows[-1]:
            rows.pop()
        return rows
    raise ParamError(f"sheet {sheet!r} not found in {ods_path}")


def load_params(ods_path: Path) -> dict[str, float]:
    rows = read_sheet(ods_path, "Params")
    params: dict[str, float] = {}
    for row in rows[1:]:  # skip the header
        if not row or not row[0].strip():
            continue
        name = row[0].strip()
        raw = row[1].strip() if len(row) > 1 else ""
        if name not in DEFAULT_PARAMS:
            raise ParamError(f"unknown param {name!r} on the Params sheet")
        try:
            params[name] = float(raw)
        except ValueError:
            raise ParamError(f"param {name!r} has a non-numeric value {raw!r}") from None
    missing = [name for name in DEFAULT_PARAMS if name not in params]
    if missing:
        raise ParamError(f"Params sheet is missing: {', '.join(missing)}")
    return params
