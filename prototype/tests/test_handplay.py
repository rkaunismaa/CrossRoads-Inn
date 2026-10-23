import shutil

import pytest

from inn_sim.deal import deal_run
from inn_sim.handplay import HANDPLAY_HEADER, deal_to_rows, read_decisions, reveal_rows
from inn_sim.params import params_from_defaults
from inn_sim.players import CarefulPlayer
from inn_sim.rules import play_run

P = params_from_defaults()
COL = {name: i for i, name in enumerate(HANDPLAY_HEADER)}


def as_sheet(rows):
    """What read_sheet would give back: every cell as text, trailing blanks dropped."""
    out = []
    for r in rows:
        r = ["" if v == "" else (str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)) for v in r]
        while r and r[-1] == "":
            r.pop()
        out.append(r)
    return out


def find_row(rows, day, slot):
    for i, r in enumerate(rows):
        if r[:1] != ["day"] and len(r) > COL["slot"] and r[COL["day"]] == str(day) and r[COL["slot"]] == str(slot):
            return i
    raise AssertionError((day, slot))


def set_cell(rows, i, col, value):
    row = rows[i] + [""] * (len(HANDPLAY_HEADER) - len(rows[i]))
    row[COL[col]] = value
    rows[i] = row


class Recorder:
    def __init__(self):
        self.inner, self.market_buys, self.decisions = CarefulPlayer(), {}, {}

    def market(self, state, day, params):
        self.market_buys[day.day] = self.inner.market(state, day, params)
        return self.market_buys[day.day]

    def decide(self, state, day, slot, view, params):
        self.decisions[(day.day, slot)] = self.inner.decide(state, day, slot, view, params)
        return self.decisions[(day.day, slot)]


def test_rows_start_with_seed_and_header():
    rows = deal_to_rows(deal_run(P, 3), P)
    assert rows[0] == ["seed=3"] and rows[1] == HANDPLAY_HEADER
    assert len(rows) == 2 + 7 * 6


def test_rows_hide_secrets():
    for seed in range(50):
        d = deal_run(P, seed)
        text = " ".join(str(c) for r in deal_to_rows(d, P) for c in r)
        assert "thief" not in text and d.final_event not in text and "final:" not in text
        assert "tier" not in text


def test_reveal_has_truth():
    d = next(deal_run(P, s) for s in range(100) if any(t.is_thief for x in deal_run(P, s).days for t in x.travelers))
    rows = reveal_rows(d)
    assert rows[-1] == ["final_event", d.final_event]
    assert any(r[3] == "yes" for r in rows[1:-1])


def test_read_decisions_round_trip():
    rows = as_sheet(deal_to_rows(deal_run(P, 2), P))
    set_cell(rows, find_row(rows, 1, 1), "decision", "accept")
    set_cell(rows, find_row(rows, 1, 1), "buy_food", "2")
    set_cell(rows, find_row(rows, 3, 2), "decision", " Decline ")
    seed, player, warnings = read_decisions(rows)
    assert seed == 2 and warnings == []
    assert player.decisions == {(1, 1): "accept", (3, 2): "decline"}
    assert player.market_buys == {1: (2, 0)}


def test_blank_decision_is_decline_with_no_warning():
    seed, player, warnings = read_decisions(as_sheet(deal_to_rows(deal_run(P, 2), P)))
    assert player.decisions == {} and warnings == []


def test_bad_decision_warns_with_row():
    rows = as_sheet(deal_to_rows(deal_run(P, 2), P))
    i = find_row(rows, 1, 2)
    set_cell(rows, i, "decision", "acept")
    _, player, warnings = read_decisions(rows)
    assert (1, 2) not in player.decisions
    assert len(warnings) == 1 and f"row {i + 1}" in warnings[0] and "acept" in warnings[0]


def test_bad_number_warns():
    rows = as_sheet(deal_to_rows(deal_run(P, 2), P))
    set_cell(rows, find_row(rows, 1, 1), "buy_food", "lots")
    _, player, warnings = read_decisions(rows)
    assert player.market_buys.get(1, (0, 0)) == (0, 0) and "lots" in warnings[0]


def test_illegal_haggle_on_non_noble_warns():
    d = deal_run(P, 2)
    rows = as_sheet(deal_to_rows(d, P))
    day, slot = next((x.day, k) for x in d.days for k, t in enumerate(x.travelers, 1) if t.kind == "pilgrim")
    set_cell(rows, find_row(rows, day, slot), "decision", "haggle_mid")
    _, player, warnings = read_decisions(rows)
    assert (day, slot) not in player.decisions and "haggle_mid" in warnings[0]


def test_missing_seed_row_raises():
    rows = as_sheet(deal_to_rows(deal_run(P, 2), P))[1:]
    with pytest.raises(ValueError, match="seed"):
        read_decisions(rows)


def test_replay_matches_play_run():
    for seed in range(20):
        d = deal_run(P, seed)
        rec = Recorder()
        expected = play_run(P, d, rec)
        rows = as_sheet(deal_to_rows(d, P))
        for day, (food, wood) in rec.market_buys.items():
            set_cell(rows, find_row(rows, day, 1), "buy_food", str(food))
            set_cell(rows, find_row(rows, day, 1), "buy_firewood", str(wood))
        for (day, slot), action in rec.decisions.items():
            set_cell(rows, find_row(rows, day, slot), "decision", action)
        got_seed, player, warnings = read_decisions(rows)
        assert got_seed == seed and warnings == []
        assert play_run(P, deal_run(P, got_seed), player) == expected


uno_only = pytest.mark.skipif(shutil.which("soffice") is None, reason="needs soffice")


@uno_only
def test_deal_keeps_params(tmp_path, monkeypatch):
    pytest.importorskip("uno")
    from inn_sim.__main__ import main
    from inn_sim.ods_write import set_params
    from inn_sim.params import load_params, read_sheet

    monkeypatch.chdir(tmp_path)
    main(["init"])
    set_params(tmp_path / "balance.ods", {"upkeep": 4})
    assert main(["deal", "--seed", "3"]) == 0
    assert load_params(tmp_path / "balance.ods")["upkeep"] == 4
    assert read_sheet(tmp_path / "balance.ods", "HandPlay")[0] == ["seed=3"]
    assert main(["replay"]) == 0


def test_dealt_columns_match_detects_param_change():
    from inn_sim.handplay import dealt_columns_match

    d = deal_run(P, 5)
    rows = as_sheet(deal_to_rows(d, P))
    set_cell(rows, find_row(rows, 1, 1), "decision", "accept")
    assert dealt_columns_match(rows, d, P)
    changed = {**P, "pay_merchant": 9, "pay_soldier": 7, "pay_pilgrim": 2, "noble_offer": 7}
    assert not dealt_columns_match(rows, deal_run(changed, 5), changed)


def test_blank_row_after_seed_still_finds_header():
    rows = as_sheet(deal_to_rows(deal_run(P, 2), P))
    set_cell(rows, find_row(rows, 1, 1), "decision", "accept")
    rows.insert(1, [])
    _, player, warnings = read_decisions(rows)
    assert player.decisions == {(1, 1): "accept"} and warnings == []


def test_missing_decision_column_raises():
    rows = as_sheet(deal_to_rows(deal_run(P, 2), P))
    rows[1] = [c for c in rows[1] if c != "decision"]
    with pytest.raises(ValueError, match="decision"):
        read_decisions(rows)


def test_blank_decision_for_arrived_traveler_warns():
    from inn_sim.handplay import blank_decision_warnings

    d = deal_run(P, 2)
    rows = as_sheet(deal_to_rows(d, P))
    set_cell(rows, find_row(rows, 1, 1), "decision", "decline")
    _, player, _ = read_decisions(rows)
    result = play_run(P, d, player)
    warnings = blank_decision_warnings(player)
    arrived = sum("slot" in line for line in result.ledger)
    assert len(warnings) == arrived - 1  # every arrived traveler except day 1 slot 1
    assert f"row {find_row(rows, 1, 2) + 1}" in warnings[0] and "treated as decline" in warnings[0]


# --- daily mode ---
from inn_sim.handplay import DAILY_HEADER, daily_rows, is_daily, last_dealt_day


def test_daily_rows_only_arrived_travelers_through_day():
    d = deal_run(P, 2)
    rows = daily_rows(d, P, {1: 3, 2: 4})
    assert rows[0] == ["seed=2", "mode=daily"] and rows[1] == DAILY_HEADER
    assert DAILY_HEADER[COL["base_arrivals"]] == "arrivals"
    body = rows[2:]
    assert [(r[0], r[5]) for r in body] == [(1, 1), (1, 2), (1, 3), (2, 1), (2, 2), (2, 3), (2, 4)]
    assert body[0][COL["base_arrivals"]] == 3  # the real count, not the dealt base


def test_daily_rows_keep_user_cells():
    d = deal_run(P, 2)
    sheet = as_sheet(daily_rows(d, P, {1: 3}))
    set_cell(sheet, find_row(sheet, 1, 2), "decision", "accept")
    set_cell(sheet, find_row(sheet, 1, 1), "buy_food", "4")
    set_cell(sheet, find_row(sheet, 1, 3), "notes", "looked shifty")
    rows = as_sheet(daily_rows(d, P, {1: 3, 2: 2}, user_rows=sheet))
    assert rows[find_row(rows, 1, 2)][COL["decision"]] == "accept"
    assert rows[find_row(rows, 1, 1)][COL["buy_food"]] == "4"
    assert rows[find_row(rows, 1, 3)][COL["notes"]] == "looked shifty"
    assert find_row(rows, 2, 2)


def test_daily_sheet_reads_back_as_decisions():
    d = deal_run(P, 2)
    sheet = as_sheet(daily_rows(d, P, {1: 3}))
    set_cell(sheet, find_row(sheet, 1, 1), "decision", "accept")
    seed, player, warnings = read_decisions(sheet)
    assert seed == 2 and player.decisions == {(1, 1): "accept"} and warnings == []


def test_daily_mode_and_last_day_detected():
    d = deal_run(P, 2)
    assert is_daily(as_sheet(daily_rows(d, P, {1: 3, 2: 4})))
    assert not is_daily(as_sheet(deal_to_rows(d, P)))
    assert last_dealt_day(as_sheet(daily_rows(d, P, {1: 3, 2: 4}))) == 2


def test_daily_rows_hide_secrets():
    for seed in range(30):
        d = deal_run(P, seed)
        text = " ".join(str(c) for r in daily_rows(d, P, {k: 3 for k in range(1, 8)}) for c in r)
        assert "thief" not in text and d.final_event not in text


@uno_only
def test_daily_cli_plays_a_week(tmp_path, monkeypatch, capsys):
    pytest.importorskip("uno")
    from inn_sim.__main__ import main
    from inn_sim.params import read_sheet

    monkeypatch.chdir(tmp_path)
    ods = tmp_path / "balance.ods"
    main(["init"])
    assert main(["deal", "--seed", "3", "--daily"]) == 0
    hp = read_sheet(ods, "HandPlay")
    assert hp[0] == ["seed=3", "mode=daily"] and {r[0] for r in hp[2:]} == {"1"}
    assert read_sheet(ods, "Reveal") == [list(read_sheet(ods, "Reveal")[0])]  # header only

    capsys.readouterr()
    assert main(["next"]) == 0
    out = capsys.readouterr().out
    assert out.index("Day 1 night") < out.index("Day 2 is dealt")  # results first, then the new day
    assert {r[0] for r in read_sheet(ods, "HandPlay")[2:]} == {"1", "2"}
    assert any("Day 1 night" in " ".join(r) for r in read_sheet(ods, "DayLog"))
    assert len(read_sheet(ods, "Reveal")) == 1

    for _ in range(10):
        if main(["next"]) != 0 or "careful" in capsys.readouterr().out:
            break
    assert any(r and r[0] == "final_event" for r in read_sheet(ods, "Reveal"))
    assert main(["next"]) == 2  # the run is over


def test_next_refuses_full_week_sheet(tmp_path, monkeypatch, capsys):
    from inn_sim.__main__ import main
    from tests.ods_fixture import make_ods
    from inn_sim.params import DEFAULT_PARAMS

    params = [["name", "value", "notes"]] + [[k, str(v), n] for k, (v, n) in DEFAULT_PARAMS.items()]
    make_ods(tmp_path / "balance.ods", {"Params": params, "HandPlay": as_sheet(deal_to_rows(deal_run(P, 1), P))})
    monkeypatch.chdir(tmp_path)
    assert main(["next"]) == 2
    assert "--daily" in capsys.readouterr().err
