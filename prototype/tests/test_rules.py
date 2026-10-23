import pytest

from inn_sim.model import DayDeal, DealtTraveler
from inn_sim.params import params_from_defaults
from inn_sim.rules import arrivals, buy, new_state, pay_upkeep, serve, traveler_view

P = params_from_defaults()


def T(kind, is_thief=False, hint=False, tier=0, news=None):
    return DealtTraveler(kind, is_thief, hint, tier, news)


def day(base=4, n=6, price_food=2, price_firewood=2, weather="normal"):
    return DayDeal(1, weather, price_food, price_firewood, False, base, tuple(T("pilgrim") for _ in range(n)))


@pytest.fixture
def s():
    return new_state(P)


def test_new_state_uses_start_params(s):
    assert (s.coins, s.food, s.firewood, s.goodwill, s.occupied) == (20, 10, 8, 0, 0)


def test_upkeep_paid(s):
    s.coins = 5
    pay_upkeep(s, P)
    assert s.coins == 2 and not s.lost


def test_upkeep_unpaid_loses(s):
    s.coins = 2
    pay_upkeep(s, P)
    assert s.lost and s.coins == 2


def test_buy_limited_by_coins(s):
    s.coins, s.food, s.firewood = 5, 0, 0
    buy(s, day(), 2, 2)
    assert (s.food, s.firewood, s.coins) == (2, 0, 1)


def test_buy_ignores_negative_amounts(s):
    buy(s, day(), -3, -1)
    assert (s.coins, s.food, s.firewood) == (20, 10, 8)


def test_merchant_accept_pays_and_uses_room_and_food(s):
    out = serve(s, T("merchant"), "accept", P)
    assert out.startswith("accepted")
    assert (s.coins, s.food, s.occupied) == (28, 9, 1)


def test_goodwill_raises_pay(s):
    s.goodwill = 4
    assert traveler_view(s, T("merchant"), P).offer == 10


def test_view_hides_thief(s):
    v = traveler_view(s, T("merchant", is_thief=True, hint=True), P)
    assert v.kind_shown == "merchant" and v.hint and v.needs_room and v.needs_meal


def test_room_full_is_decline(s):
    s.occupied = 3
    assert serve(s, T("soldier"), "accept", P).startswith("declined")
    assert s.coins == 20


def test_no_food_is_decline(s):
    s.food = 0
    assert serve(s, T("pilgrim"), "accept", P).startswith("declined")
    assert s.goodwill == 0


def test_haggle_on_non_noble_is_decline(s):
    assert serve(s, T("soldier"), "haggle_mid", P).startswith("declined")
    assert (s.coins, s.occupied) == (20, 0)


def test_noble_accept_pays_offer(s):
    serve(s, T("noble", tier=0), "accept", P)
    assert (s.coins, s.occupied) == (26, 1)


def test_noble_haggle_within_tier_pays_ask(s):
    serve(s, T("noble", tier=1), "haggle_mid", P)
    assert (s.coins, s.occupied) == (30, 1)


def test_noble_haggle_high_within_tier(s):
    serve(s, T("noble", tier=2), "haggle_high", P)
    assert s.coins == 35


def test_noble_haggle_over_tier_walks_out(s):
    s.goodwill = 1
    out = serve(s, T("noble", tier=0), "haggle_mid", P)
    assert "walked out" in out
    assert (s.coins, s.occupied, s.goodwill, s.walkout_yesterday) == (20, 0, 0, True)


def test_pilgrim_raises_goodwill_capped(s):
    s.goodwill = 10
    serve(s, T("pilgrim"), "accept", P)
    assert s.goodwill == 10 and s.coins == 22  # round(1 * 1.5)


def test_wanderer_adds_news_no_coins(s):
    serve(s, T("wanderer", news="final:robbery"), "accept", P)
    assert s.news == ["final:robbery"] and s.coins == 20 and s.food == 9


def test_accepted_thief_counts_for_tonight(s):
    serve(s, T("merchant", is_thief=True), "accept", P)
    assert s.thieves_tonight == 1 and s.coins == 28


def test_decline_changes_nothing(s):
    serve(s, T("merchant"), "decline", P)
    assert (s.coins, s.food, s.occupied) == (20, 10, 0)


def test_arrivals_bonus_and_walkout_penalty(s):
    assert arrivals(s, day(4), P) == 4
    s.goodwill = 5
    assert arrivals(s, day(4), P) == 5
    s.walkout_yesterday = True
    assert arrivals(s, day(4), P) == 4
    s.goodwill = 0
    assert arrivals(s, day(4), P) == 3
    s.goodwill = 5
    s.walkout_yesterday = False
    assert arrivals(s, day(5, n=5), P) == 5  # never above the dealt slots
