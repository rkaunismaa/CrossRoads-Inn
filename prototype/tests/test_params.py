import pytest

from inn_sim.params import DEFAULT_PARAMS, ParamError, load_params, params_from_defaults, read_sheet
from tests.ods_fixture import make_ods

HEADER = ["name", "value", "notes"]


def _rows(drop: str | None = None, extra: list | None = None, override: dict | None = None):
    rows = [HEADER]
    for name, (value, note) in DEFAULT_PARAMS.items():
        if name == drop:
            continue
        rows.append([name, (override or {}).get(name, str(value)), note])
    if extra:
        rows.append(extra)
    return rows


def test_load_params_reads_values(tmp_path):
    p = make_ods(tmp_path / "b.ods", {"Params": _rows()})
    assert load_params(p) == params_from_defaults()


def test_missing_param_names_it(tmp_path):
    p = make_ods(tmp_path / "b.ods", {"Params": _rows(drop="upkeep")})
    with pytest.raises(ParamError, match="upkeep"):
        load_params(p)


def test_unknown_param_names_it(tmp_path):
    p = make_ods(tmp_path / "b.ods", {"Params": _rows(extra=["upkep", "3", ""])})
    with pytest.raises(ParamError, match="upkep"):
        load_params(p)


def test_non_numeric_value_names_it(tmp_path):
    p = make_ods(tmp_path / "b.ods", {"Params": _rows(override={"upkeep": "ten"})})
    with pytest.raises(ParamError, match="upkeep.*ten"):
        load_params(p)


def test_read_sheet_expands_repeated_cells(tmp_path):
    p = make_ods(tmp_path / "b.ods", {"S": [["a", ("x", 3), "b"]]})
    assert read_sheet(p, "S") == [["a", "x", "x", "x", "b"]]


def test_read_sheet_drops_trailing_empties(tmp_path):
    p = make_ods(tmp_path / "b.ods", {"S": [["a", "", ""], ["", ""], ["b"], ["", ""]]})
    assert read_sheet(p, "S") == [["a"], [], ["b"]]


def test_missing_sheet_raises(tmp_path):
    with pytest.raises(ParamError, match="Params"):
        load_params(make_ods(tmp_path / "b.ods", {"Other": []}))


def test_defaults_cover_rule_model():
    for key in ["start_coins", "debt", "upkeep", "rooms", "p_snow", "blizzard_mult", "thief_p",
                "noble_high", "robbery_safe_goodwill", "goodwill_cap", "hungry_soldiers_food"]:
        assert key in DEFAULT_PARAMS
