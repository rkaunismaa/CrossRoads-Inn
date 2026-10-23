import shutil

import pytest

pytest.importorskip("uno")
if shutil.which("soffice") is None:
    pytest.skip("soffice not installed", allow_module_level=True)

from inn_sim.__main__ import main  # noqa: E402
from inn_sim.ods_write import WorkbookLocked, create_workbook, set_params, write_sheet  # noqa: E402
from inn_sim.params import DEFAULT_PARAMS, ParamError, load_params, params_from_defaults, read_sheet  # noqa: E402


def test_create_then_load_round_trips(tmp_path):
    p = tmp_path / "b.ods"
    create_workbook(p)
    assert load_params(p) == params_from_defaults()
    assert read_sheet(p, "HandPlay") and read_sheet(p, "Reveal")


def test_create_refuses_existing(tmp_path):
    p = tmp_path / "b.ods"
    p.write_text("x")
    with pytest.raises(FileExistsError):
        create_workbook(p)


def test_write_sheet_leaves_other_sheets(tmp_path):
    p = tmp_path / "b.ods"
    create_workbook(p)
    set_params(p, {"upkeep": 4})
    write_sheet(p, "HandPlay", [["x", 1.5]])
    assert load_params(p)["upkeep"] == 4
    assert read_sheet(p, "HandPlay") == [["x", "1.5"]]


def test_write_sheet_clears_old_rows(tmp_path):
    p = tmp_path / "b.ods"
    create_workbook(p)
    write_sheet(p, "HandPlay", [["a"], ["b"], ["c"]])
    write_sheet(p, "HandPlay", [["z"]])
    assert read_sheet(p, "HandPlay") == [["z"]]


def test_set_params_keeps_notes(tmp_path):
    p = tmp_path / "b.ods"
    create_workbook(p)
    set_params(p, {"debt": 70})
    row = next(r for r in read_sheet(p, "Params") if r[0] == "debt")
    assert row == ["debt", "70", DEFAULT_PARAMS["debt"][1]]


def test_set_params_rejects_unknown(tmp_path):
    p = tmp_path / "b.ods"
    create_workbook(p)
    with pytest.raises(ParamError, match="dbet"):
        set_params(p, {"dbet": 70})


def test_locked_workbook_refused(tmp_path):
    p = tmp_path / "b.ods"
    create_workbook(p)
    (tmp_path / ".~lock.b.ods#").write_text("x")
    with pytest.raises(WorkbookLocked, match="close"):
        write_sheet(p, "HandPlay", [])


def test_cli_init(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["init"]) == 0
    assert load_params(tmp_path / "balance.ods") == params_from_defaults()
