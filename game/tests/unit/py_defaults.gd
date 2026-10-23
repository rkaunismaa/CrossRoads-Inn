extends RefCounted
## Test helper: Python's DEFAULT_PARAMS, so rule tests can reuse the Python tests' exact numbers.
## The fixture params are the tuned values; these are the ones tuning changed.

const OVERRIDES := {
	"start_coins": 20.0, "rooms": 3.0, "debt": 60.0, "robbery_frac": 0.4, "thief_steal_frac": 0.3,
	"thief_p": 0.3, "goodwill_pay_bonus": 0.05, "noble_high": 15.0,
}


static func params() -> Dictionary:
	var f: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://tests/fixtures/careful_0.json"))
	var p := {}
	for key: String in f.params:
		p[key] = float(f.params[key])
	p.merge(OVERRIDES, true)
	return p


static func traveler(kind: String, is_thief := false, hint := false, tier := 0, news := "") -> DealtTraveler:
	return DealtTraveler.new(kind, is_thief, hint, tier, news)


static func day(base := 4, n := 6, price_food := 2, price_firewood := 2, weather := "normal") -> DayDeal:
	var d := DayDeal.new()
	d.day = 1
	d.weather = weather
	d.price_food = price_food
	d.price_firewood = price_firewood
	d.base_arrivals = base
	for i in n:
		d.travelers.append(traveler("pilgrim"))
	return d
