import json
from pathlib import Path

from inn_sim.export import export_params, params_for_export
from inn_sim.params import DEFAULT_PARAMS, load_params, params_from_defaults

P = params_from_defaults()
ROOT = Path(__file__).resolve().parents[2]


def test_export_params_round_trips(tmp_path):
    export_params(P, tmp_path / "p.json")
    data = json.loads((tmp_path / "p.json").read_text())
    assert list(data) == list(DEFAULT_PARAMS)
    assert data["rooms"] == 3 and isinstance(data["rooms"], int)
    assert data["days"] == 7 and isinstance(data["days"], int)
    assert data["thief_p"] == 0.3 and isinstance(data["debt"], float)


def test_game_params_match_workbook():
    game = json.loads((ROOT / "game/data/params.json").read_text())
    expected = json.loads(json.dumps(params_for_export(load_params(ROOT / "prototype/balance.ods"))))
    assert game == expected, "game/data/params.json is stale: run `cd prototype && python3 -m inn_sim export`"
