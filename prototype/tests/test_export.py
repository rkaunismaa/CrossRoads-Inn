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


# --- parity fixtures ---
from inn_sim.deal import deal_run  # noqa: E402
from inn_sim.export import REQUIRED_MARKERS, deal_from_dict, export_fixtures, fixture_dict, params_hash  # noqa: E402
from inn_sim.players import CarefulPlayer, RecordingPlayer, ScriptedPlayer  # noqa: E402
from inn_sim.rules import play_run  # noqa: E402


def test_fixture_replays_to_its_ledger():
    f = fixture_dict("careful_3", P, deal_run(P, 3), RecordingPlayer(CarefulPlayer()))
    player = ScriptedPlayer({int(d): tuple(v) for d, v in f["market"].items()},
                            {(d, s): a for d, s, a in f["decisions"]})
    assert list(play_run(P, deal_run(P, 3), player).ledger) == f["ledger"]
    assert f["result"]["end_coins"] == play_run(P, deal_run(P, 3), CarefulPlayer()).end_coins


def test_fixture_deal_round_trips():
    f = fixture_dict("careful_3", P, deal_run(P, 3), RecordingPlayer(CarefulPlayer()))
    assert deal_from_dict(json.loads(json.dumps(f["deal"]))) == deal_run(P, 3)


def test_export_covers_every_marker(tmp_path):
    names = export_fixtures(P, tmp_path)
    assert len(names) >= 20 and (tmp_path / "manifest.json").exists()
    text = "\n".join(line for n in names for line in json.loads((tmp_path / n).read_text())["ledger"])
    for marker in REQUIRED_MARKERS:
        assert marker in text, marker


def test_export_removes_old_fixtures(tmp_path):
    (tmp_path / "stale.json").write_text("{}")
    export_fixtures(P, tmp_path)
    assert not (tmp_path / "stale.json").exists()


def test_committed_fixtures_match_workbook():
    manifest = json.loads((ROOT / "game/tests/fixtures/manifest.json").read_text())
    assert manifest["params_hash"] == params_hash(load_params(ROOT / "prototype/balance.ods")), \
        "fixtures are stale: run `cd prototype && python3 -m inn_sim export-fixtures`"
