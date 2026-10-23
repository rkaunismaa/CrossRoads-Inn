extends GutTest
## Bram reads facts and returns text. He never sees secrets and never changes the game.

const D := preload("res://tests/unit/py_defaults.gd")
const SECRETS := ["is_thief", "noble_tier", "goodwill"]
var P: Dictionary


func before_all() -> void:
	P = D.params()


## Play a whole Godot-dealt run (accepting everyone), collecting every facts dict Bram would see.
func _all_facts(seed: int) -> Array[Dictionary]:
	var out: Array[Dictionary] = []
	var r := DayRunner.new(P, Dealer.deal_run(P, seed))
	while not r.is_over():
		if not r.begin_day():
			break
		r.buy(0, 0)
		out.append(BramFacts.morning(r, P))
		while r.has_traveler():
			out.append(BramFacts.traveler(r, P))
			r.decide("accept")
		out.append(BramFacts.night(r, r.end_day(), P))
	return out


func test_facts_never_leak_secrets() -> void:
	for seed in 20:
		var facts := _all_facts(seed)
		for f in facts:
			for key in SECRETS:
				assert_false(f.has(key), "%s in %s facts" % [key, f.moment])
			if f.moment == "night" and f.final_event != "":
				assert_eq(f.day, int(P.days), "final event only on the last night")
		# A morning never names a final event unless a wanderer announced it.
		for f in facts:
			if f.moment != "morning" or f.news.any(func(n: String) -> bool: return n.begins_with("the final night")):
				continue
			for event in ["blizzard", "robbery", "hungry soldiers"]:
				assert_false(str(f.values()).contains(event), "morning facts name %s unannounced" % event)


func test_moment_keys_are_documented_shape() -> void:
	var facts := _all_facts(3)
	var morning: Dictionary = facts[0]
	for key in ["moment", "day", "weather", "travelers_coming", "food_low", "firewood_short_tonight", "cheap_firewood", "news", "final_night"]:
		assert_true(morning.has(key), key)
	var traveler: Dictionary = facts[1]
	for key in ["moment", "day", "kind", "suspicious", "needs_room", "needs_meal", "offer", "rooms_full", "food_low"]:
		assert_true(traveler.has(key), key)
	var night: Dictionary = facts.filter(func(f: Dictionary) -> bool: return f.moment == "night")[0]
	for key in ["moment", "day", "shortage", "theft", "final_event", "coins", "food", "firewood"]:
		assert_true(night.has(key), key)


func test_bram_does_not_change_state() -> void:
	var r := DayRunner.new(P, Dealer.deal_run(P, 1))
	r.begin_day()
	r.buy(0, 0)
	var bram := Bram.new(1)
	var before := r.state.snapshot()
	var ledger_before := r.ledger.size()
	bram.line_for(BramFacts.morning(r, P))
	bram.line_for(BramFacts.traveler(r, P))
	assert_eq(r.state.snapshot(), before)
	assert_eq(r.ledger.size(), ledger_before)


func test_suspicious_merchant_gets_a_warning() -> void:
	var facts := {"moment": "traveler", "day": 2, "kind": "merchant", "suspicious": true, "needs_room": true,
		"needs_meal": true, "offer": 8, "rooms_full": false, "food_low": false}
	assert_eq(Bram.situation_for(facts), "traveler_suspicious")
	assert_true(Bram.new(4).line_for(facts) in Bram.LINES["traveler_suspicious"].map(func(l: String) -> String: return l.format(facts)))


func test_situation_priorities() -> void:
	var m := {"moment": "morning", "day": 7, "weather": "snow", "travelers_coming": 4, "food_low": true,
		"firewood_short_tonight": true, "cheap_firewood": true, "news": [], "final_night": true}
	assert_eq(Bram.situation_for(m), "morning_final_night")
	m.final_night = false
	assert_eq(Bram.situation_for(m), "morning_firewood_short")
	m.firewood_short_tonight = false
	assert_eq(Bram.situation_for(m), "morning_food_low")
	var n := {"moment": "night", "day": 3, "shortage": true, "theft": true, "final_event": "", "coins": 1, "food": 1, "firewood": 0}
	assert_eq(Bram.situation_for(n), "night_theft")
	var t := {"moment": "traveler", "day": 1, "kind": "soldier", "suspicious": false, "needs_room": true,
		"needs_meal": false, "offer": 6, "rooms_full": true, "food_low": false}
	assert_eq(Bram.situation_for(t), "traveler_rooms_full")
	t.rooms_full = false
	assert_eq(Bram.situation_for(t), "traveler_soldier")


func test_every_situation_has_two_variants() -> void:
	for situation: String in Bram.LINES:
		assert_gte(Bram.LINES[situation].size(), 2, situation)


func test_every_line_formats_cleanly() -> void:
	for facts in _all_facts(5):
		var line := Bram.new(0).line_for(facts)
		assert_ne(line, "")
		assert_false(line.contains("{"), line)


func test_same_seed_same_lines() -> void:
	var facts := _all_facts(2)
	var a := Bram.new(9)
	var b := Bram.new(9)
	for f in facts:
		assert_eq(a.line_for(f), b.line_for(f))
