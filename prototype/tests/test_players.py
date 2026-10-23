from inn_sim.deal import deal_run
from inn_sim.model import DayView, TravelerView
from inn_sim.params import params_from_defaults
from inn_sim.players import CarefulPlayer, RandomPlayer, ScriptedPlayer
from inn_sim.rules import new_state, play_run

P = params_from_defaults()
DAY = DayView(1, "normal", 2, 2, 4)


def V(kind, hint=False, offer=8, room=True, meal=False):
    return TravelerView(kind, hint, offer, room, meal)


def test_random_player_only_picks_legal_actions():
    for seed in range(500):
        r = play_run(P, deal_run(P, seed), RandomPlayer(seed))
        assert not any("declined (" in line for line in r.ledger), (seed, r.ledger)


def test_random_player_is_seeded():
    d = deal_run(P, 9)
    assert play_run(P, d, RandomPlayer(3)) == play_run(P, d, RandomPlayer(3))


def test_careful_declines_hinted_merchant():
    s = new_state(P)
    assert CarefulPlayer().decide(s, DAY, 1, V("merchant", hint=True, meal=True), P) == "decline"
    assert CarefulPlayer().decide(s, DAY, 1, V("merchant", meal=True), P) == "accept"


def test_careful_refuses_room_without_firewood():
    s = new_state(P)
    s.firewood, s.occupied = 2, 1  # fire_need(2, normal) == 3
    assert CarefulPlayer().decide(s, DAY, 1, V("soldier"), P) == "decline"
    s.firewood = 3
    assert CarefulPlayer().decide(s, DAY, 1, V("soldier"), P) == "accept"


def test_careful_haggles_noble_only_at_low_goodwill():
    s = new_state(P)
    assert CarefulPlayer().decide(s, DAY, 1, V("noble", offer=6), P) == "haggle_mid"
    s.goodwill = 3
    assert CarefulPlayer().decide(s, DAY, 1, V("noble", offer=6), P) == "accept"


def test_careful_feeds_pilgrim_only_with_spare_food():
    s = new_state(P)
    s.food = 3  # 4 arrivals, this is slot 1: 3 still to come
    assert CarefulPlayer().decide(s, DAY, 1, V("pilgrim", room=False, meal=True), P) == "decline"
    s.food = 4
    assert CarefulPlayer().decide(s, DAY, 1, V("pilgrim", room=False, meal=True), P) == "accept"


def test_careful_never_spends_below_upkeep_reserve():
    s = new_state(P)
    s.food, s.firewood, s.coins = 0, 0, 30
    food, wood = CarefulPlayer().market(s, DAY, P)
    reserve = 3 * 6 + 2
    assert food * 2 + wood * 2 <= 30 - reserve
    assert food + wood > 0


def test_careful_stocks_up_when_blizzard_is_known():
    s = new_state(P)
    s.coins, s.firewood, s.food = 200, 0, 50
    last = DayView(7, "normal", 2, 2, 4)
    plain = CarefulPlayer().market(s, last, P)[1]
    s.news.append("final:blizzard")
    assert CarefulPlayer().market(s, last, P)[1] > plain


def test_scripted_player_replays_decisions():
    p = ScriptedPlayer({1: (2, 3)}, {(1, 2): "accept"})
    s = new_state(P)
    assert p.market(s, DAY, P) == (2, 3)
    assert p.market(s, DayView(2, "normal", 2, 2, 4), P) == (0, 0)
    assert p.decide(s, DAY, 2, V("soldier"), P) == "accept"
    assert p.decide(s, DAY, 1, V("soldier"), P) == "decline"


def test_careful_beats_random_on_defaults():
    careful = random = 0
    for seed in range(300):
        d = deal_run(P, seed)
        careful += play_run(P, d, CarefulPlayer()).won
        random += play_run(P, d, RandomPlayer(seed)).won
    assert careful > random
