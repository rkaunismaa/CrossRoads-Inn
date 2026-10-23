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
