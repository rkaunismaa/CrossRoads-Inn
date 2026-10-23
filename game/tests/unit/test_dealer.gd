extends GutTest
## Mirrors prototype/tests/test_deal.py: Godot deals its own runs with the same odds as Python.

const D := preload("res://tests/unit/py_defaults.gd")
var P: Dictionary


func before_all() -> void:
	P = D.params()


func _travelers(seeds: int) -> Array[DealtTraveler]:
	var out: Array[DealtTraveler] = []
	for s in seeds:
		for d: DayDeal in Dealer.deal_run(P, s).days:
			out.append_array(d.travelers)
	return out


func _same(a: RunDeal, b: RunDeal) -> bool:
	if a.final_event != b.final_event or a.days.size() != b.days.size():
		return false
	for i in a.days.size():
		var x := a.days[i]
		var y := b.days[i]
		if [x.weather, x.price_food, x.price_firewood, x.cheap_day, x.base_arrivals] != [y.weather, y.price_food, y.price_firewood, y.cheap_day, y.base_arrivals]:
			return false
		for j in x.travelers.size():
			var t := x.travelers[j]
			var u := y.travelers[j]
			if [t.kind, t.is_thief, t.hint, t.noble_tier, t.news] != [u.kind, u.is_thief, u.hint, u.noble_tier, u.news]:
				return false
	return true


func test_same_seed_same_deal() -> void:
	assert_true(_same(Dealer.deal_run(P, 7), Dealer.deal_run(P, 7)))


func test_different_seeds_differ() -> void:
	assert_false(_same(Dealer.deal_run(P, 1), Dealer.deal_run(P, 2)))


func test_shape() -> void:
	var d := Dealer.deal_run(P, 3)
	assert_eq(d.seed, 3)
	assert_eq(d.days.size(), 7)
	for i in 7:
		assert_eq(d.days[i].day, i + 1)
		assert_eq(d.days[i].travelers.size(), 6)
		assert_between(d.days[i].base_arrivals, 3, 5)
	assert_true(d.final_event in ["blizzard", "hungry_soldiers", "robbery"])


func test_only_merchants_can_be_thieves() -> void:
	var any_thief := false
	for t in _travelers(200):
		if t.is_thief:
			any_thief = true
			assert_eq(t.kind, "merchant")
	assert_true(any_thief)


func test_only_wanderers_carry_news_and_hints_only_merchants() -> void:
	for t in _travelers(200):
		assert_eq(t.news != "", t.kind == "wanderer")
		if t.hint:
			assert_eq(t.kind, "merchant")


func test_news_tells_the_truth() -> void:
	for s in 200:
		var d := Dealer.deal_run(P, s)
		for day: DayDeal in d.days:
			for t: DealtTraveler in day.travelers:
				if t.news == "":
					continue
				var parts := t.news.split(":", true, 1)
				if parts[0] == "final":
					assert_eq(parts[1], d.final_event)
				elif parts[0] == "weather":
					var w := parts[1].split("=")
					assert_eq(int(w[0]), day.day + 1)
					assert_eq(d.days[int(w[0]) - 1].weather, w[1])
				else:
					assert_eq(parts[0], "cheap")
					var later := "none"
					for x: DayDeal in d.days:
						if x.day > day.day and x.cheap_day:
							later = str(x.day)
							break
					assert_eq(parts[1], later)


func test_only_nobles_have_tiers() -> void:
	var tiers := {}
	for t in _travelers(200):
		if t.kind == "noble":
			tiers[t.noble_tier] = true
		else:
			assert_eq(t.noble_tier, 0)
	assert_eq(tiers.keys().size(), 3)


func test_weather_frequencies_roughly_match_params() -> void:
	var n := 0
	var snow := 0
	var cold := 0
	for s in 286:
		for d: DayDeal in Dealer.deal_run(P, s).days:
			n += 1
			snow += int(d.weather == "snow")
			cold += int(d.weather == "cold")
	assert_almost_eq(float(snow) / n, 0.15, 0.03)
	assert_almost_eq(float(cold) / n, 0.30, 0.04)


func test_cheap_day_prices() -> void:
	var any_cheap := false
	for s in 200:
		for d: DayDeal in Dealer.deal_run(P, s).days:
			assert_gte(d.price_food, 1)
			assert_gte(d.price_firewood, 1)
			if d.cheap_day:
				any_cheap = true
				assert_lte(d.price_firewood, InnRules.py_round(2 * 1.25 * 0.5))
	assert_true(any_cheap)
