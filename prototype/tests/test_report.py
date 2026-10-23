import pytest

import inn_sim.report as report
from inn_sim.__main__ import main
from inn_sim.params import params_from_defaults
from inn_sim.report import Stats, check_bar, sensitivity, simulate

P = params_from_defaults()
OK = {"careful": Stats(100, 0.75, 66, 0.10), "random": Stats(100, 0.1, 40, -0.33)}


def test_simulate_is_deterministic():
    assert simulate(P, 200, 5) == simulate(P, 200, 5)


def test_simulate_stats_shape():
    st = simulate(P, 100, 0)
    assert set(st) == {"careful", "random"}
    c = st["careful"]
    assert c.runs == 100 and 0 <= c.win_rate <= 1
    assert abs(c.median_margin - (c.median_end - 60) / 60) < 1e-9


def test_check_bar_messages():
    assert check_bar(OK) == []
    assert any("careful win rate" in m for m in check_bar({**OK, "careful": Stats(100, 0.9, 66, 0.10)}))
    assert any("margin" in m for m in check_bar({**OK, "careful": Stats(100, 0.75, 80, 0.33)}))
    assert any("random" in m for m in check_bar({**OK, "random": Stats(100, 0.3, 50, -0.1)}))


def test_bar_edges_inclusive():
    for win, margin in [(0.70, 0.0), (0.80, 0.15)]:
        assert check_bar({**OK, "careful": Stats(100, win, 0, margin)}) == []
    assert check_bar({**OK, "random": Stats(100, 0.20, 0, 0)}) != []


def test_sensitivity_flags_breaking_param(monkeypatch):
    def fake(params, runs, seed):
        win = 0.5 if params["debt"] == 66 else 0.75
        return {"careful": Stats(runs, win, 0, 0), "random": Stats(runs, 0, 0, 0)}

    monkeypatch.setattr(report, "simulate", fake)
    assert sensitivity(P, 10, 0) == [("debt", 1.1, 0.5)]


def test_small_whole_numbers_are_not_nudged(monkeypatch):
    seen = []

    def fake(params, runs, seed):
        seen.append(params)
        return {"careful": Stats(runs, 0.75, 0, 0), "random": Stats(runs, 0, 0, 0)}

    monkeypatch.setattr(report, "simulate", fake)
    sensitivity(P, 10, 0)
    assert all(p["upkeep"] == 3 and p["food_per_meal"] == 1 for p in seen)  # 3*1.1 rounds back to 3
    assert "upkeep" in report.untested_params(P) and "debt" not in report.untested_params(P)


def test_sensitivity_skips_structural_params(monkeypatch):
    seen = []

    def fake(params, runs, seed):
        seen.append(params)
        return {"careful": Stats(runs, 0.75, 0, 0), "random": Stats(runs, 0, 0, 0)}

    monkeypatch.setattr(report, "simulate", fake)
    sensitivity(P, 10, 0)
    assert all(p["days"] == 7 and p["travelers_min"] == 3 and p["travelers_max"] == 5 for p in seen)
    assert all(0 <= p["thief_p"] <= 1 and p["start_goodwill"] >= 0 for p in seen)


def test_cli_simulate_prints_bar(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # no balance.ods here: falls back to defaults
    main(["simulate", "--runs", "50"])
    out = capsys.readouterr()
    assert "BAR:" in out.out and "careful" in out.out
    assert "DEFAULT_PARAMS" in out.err


def test_cli_simulate_writes_csv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main(["simulate", "--runs", "20", "--csv", "runs.csv"])
    lines = (tmp_path / "runs.csv").read_text().splitlines()
    assert lines[0].startswith("seed,") and len(lines) == 21


def test_fraction_friendly_params_are_nudged():
    untested = report.untested_params(P)
    for name in ("price_food", "price_firewood", "w_merchant", "w_wanderer",
                 "pay_pilgrim", "robbery_safe_goodwill"):
        assert name not in untested
    assert report._nudge("price_food", 2, 1.1) == pytest.approx(2.2)
    assert report._nudge("fire_base", 1, 1.1) == 1  # whole firewood, rounded up by the rules
