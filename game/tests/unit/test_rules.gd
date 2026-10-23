extends GutTest
## Mirrors prototype/tests/test_rules.py with the same numbers (Python's default params).

const D := preload("res://tests/unit/py_defaults.gd")
var P: Dictionary
var s: InnState


func before_each() -> void:
	P = D.params()
	s = InnRules.new_state(P)


func test_py_round_half_even() -> void:
	assert_eq(InnRules.py_round(2.5), 2)
	assert_eq(InnRules.py_round(3.5), 4)
	assert_eq(InnRules.py_round(9.6), 10)
	assert_eq(InnRules.py_round(1.5), 2)
	assert_eq(InnRules.py_round(-0.5), 0)


func test_new_state_uses_start_params() -> void:
	assert_eq([s.coins, s.food, s.firewood, s.goodwill, s.occupied], [20, 10, 8, 0, 0])


func test_upkeep_paid() -> void:
	s.coins = 5
	InnRules.pay_upkeep(s, P)
	assert_eq(s.coins, 2)
	assert_false(s.lost)


func test_upkeep_unpaid_loses() -> void:
	s.coins = 2
	InnRules.pay_upkeep(s, P)
	assert_true(s.lost)
	assert_eq(s.coins, 2)


func test_buy_limited_by_coins() -> void:
	s.coins = 5; s.food = 0; s.firewood = 0
	InnRules.buy(s, D.day(), 2, 2)
	assert_eq([s.food, s.firewood, s.coins], [2, 0, 1])


func test_buy_ignores_negative_amounts() -> void:
	InnRules.buy(s, D.day(), -3, -1)
	assert_eq([s.coins, s.food, s.firewood], [20, 10, 8])


func test_merchant_accept_pays_and_uses_room_and_food() -> void:
	assert_string_starts_with(InnRules.serve(s, D.traveler("merchant"), "accept", P), "accepted")
	assert_eq([s.coins, s.food, s.occupied], [28, 9, 1])


func test_goodwill_raises_pay() -> void:
	s.goodwill = 4
	assert_eq(InnRules.traveler_view(s, D.traveler("merchant"), P).offer, 10)


func test_view_hides_thief() -> void:
	var v := InnRules.traveler_view(s, D.traveler("merchant", true, true), P)
	assert_eq(v.kind_shown, "merchant")
	assert_true(v.hint and v.needs_room and v.needs_meal)


func test_room_full_is_decline() -> void:
	s.occupied = 3
	assert_string_starts_with(InnRules.serve(s, D.traveler("soldier"), "accept", P), "declined")
	assert_eq(s.coins, 20)


func test_no_food_is_decline() -> void:
	s.food = 0
	assert_string_starts_with(InnRules.serve(s, D.traveler("pilgrim"), "accept", P), "declined")
	assert_eq(s.goodwill, 0)


func test_haggle_on_non_noble_is_decline() -> void:
	assert_eq(InnRules.serve(s, D.traveler("soldier"), "haggle_mid", P), "declined (can't haggle)")
	assert_eq([s.coins, s.occupied], [20, 0])


func test_noble_accept_pays_offer() -> void:
	InnRules.serve(s, D.traveler("noble"), "accept", P)
	assert_eq([s.coins, s.occupied], [26, 1])


func test_noble_haggle_within_tier_pays_ask() -> void:
	InnRules.serve(s, D.traveler("noble", false, false, 1), "haggle_mid", P)
	assert_eq([s.coins, s.occupied], [30, 1])


func test_noble_haggle_high_within_tier() -> void:
	InnRules.serve(s, D.traveler("noble", false, false, 2), "haggle_high", P)
	assert_eq(s.coins, 35)


func test_noble_haggle_over_tier_walks_out() -> void:
	s.goodwill = 1
	assert_eq(InnRules.serve(s, D.traveler("noble"), "haggle_mid", P), "noble walked out")
	assert_eq([s.coins, s.occupied, s.goodwill, s.walkout_yesterday], [20, 0, 0, true])


func test_pilgrim_raises_goodwill_capped() -> void:
	s.goodwill = 10
	InnRules.serve(s, D.traveler("pilgrim"), "accept", P)
	assert_eq([s.goodwill, s.coins], [10, 22])


func test_wanderer_adds_news_no_coins() -> void:
	var out := InnRules.serve(s, D.traveler("wanderer", false, false, 0, "weather:3=snow"), "accept", P)
	assert_eq(out, "accepted +0, news: day 3 will be snow")
	assert_eq(Array(s.news), ["weather:3=snow"])
	assert_eq([s.coins, s.food], [20, 9])


func test_accepted_thief_counts_for_tonight() -> void:
	InnRules.serve(s, D.traveler("merchant", true), "accept", P)
	assert_eq([s.thieves_tonight, s.coins], [1, 28])


func test_decline_changes_nothing() -> void:
	assert_eq(InnRules.serve(s, D.traveler("merchant"), "decline", P), "declined")
	assert_eq([s.coins, s.food, s.occupied], [20, 10, 0])


func test_arrivals_bonus_and_walkout_penalty() -> void:
	assert_eq(InnRules.arrivals(s, D.day(4), P), 4)
	s.goodwill = 5
	assert_eq(InnRules.arrivals(s, D.day(4), P), 5)
	s.walkout_yesterday = true
	assert_eq(InnRules.arrivals(s, D.day(4), P), 4)
	s.goodwill = 0
	assert_eq(InnRules.arrivals(s, D.day(4), P), 3)
	s.goodwill = 5
	s.walkout_yesterday = false
	assert_eq(InnRules.arrivals(s, D.day(5, 5), P), 5)


func test_refusal_reasons() -> void:
	assert_eq(InnRules.refusal_reason(s, D.traveler("soldier"), "accept", P), "")
	s.occupied = 3
	assert_eq(InnRules.refusal_reason(s, D.traveler("soldier"), "accept", P), "no room")
	s.occupied = 0
	s.food = 0
	assert_eq(InnRules.refusal_reason(s, D.traveler("pilgrim"), "accept", P), "no food")
	assert_eq(InnRules.refusal_reason(s, D.traveler("soldier"), "haggle_mid", P), "can't haggle")
	assert_eq(InnRules.refusal_reason(s, D.traveler("soldier"), "decline", P), "")


func test_describe_news() -> void:
	assert_eq(InnRules.describe_news("weather:3=snow"), "day 3 will be snow")
	assert_eq(InnRules.describe_news("cheap:5"), "firewood is cheap on day 5")
	assert_eq(InnRules.describe_news("cheap:none"), "no cheap firewood days ahead")
	assert_eq(InnRules.describe_news("final:hungry_soldiers"), "the final night brings: hungry soldiers")
