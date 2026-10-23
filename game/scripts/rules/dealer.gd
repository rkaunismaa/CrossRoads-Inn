class_name Dealer
extends RefCounted
## Rolls every random outcome of a run up front, like prototype/inn_sim/deal.py: same odds and roll
## order, but Godot's RandomNumberGenerator, so a seed does not give the same run as Python.

const KINDS: PackedStringArray = ["merchant", "pilgrim", "soldier", "noble", "wanderer"]
const FINAL_EVENTS: PackedStringArray = ["blizzard", "hungry_soldiers", "robbery"]


static func deal_run(p: Dictionary, seed: int) -> RunDeal:
	var rng := RandomNumberGenerator.new()
	rng.seed = seed
	var deal := RunDeal.new()
	deal.seed = seed
	var jitter: float = p.price_jitter

	# Day facts first, so news can tell the truth about later days.
	for n in int(p.days):
		var d := DayDeal.new()
		d.day = n + 1
		d.weather = _weather(rng, p)
		d.cheap_day = rng.randf() < p.p_cheap_day
		d.price_food = _price(rng, p.price_food, jitter, 1.0)
		d.price_firewood = _price(rng, p.price_firewood, jitter, p.cheap_discount if d.cheap_day else 1.0)
		d.base_arrivals = rng.randi_range(int(p.travelers_min), int(p.travelers_max))
		deal.days.append(d)
	deal.final_event = FINAL_EVENTS[rng.randi_range(0, FINAL_EVENTS.size() - 1)]

	var weights: Array[float] = []
	for kind in KINDS:
		weights.append(float(p["w_" + kind]))
	for d: DayDeal in deal.days:
		for i in int(p.travelers_max) + 1:
			var kind := _weighted(rng, weights)
			var is_thief: bool = kind == "merchant" and rng.randf() < p.thief_p
			var hint_p: float = p.hint_accuracy if is_thief else p.hint_false_pos
			var hint: bool = kind == "merchant" and rng.randf() < hint_p
			var tier := _noble_tier(rng, p) if kind == "noble" else 0
			var news := _news(rng, d.day, deal) if kind == "wanderer" else ""
			d.travelers.append(DealtTraveler.new(kind, is_thief, hint, tier, news))
	return deal


static func _weather(rng: RandomNumberGenerator, p: Dictionary) -> String:
	var u := rng.randf()
	if u < p.p_snow:
		return "snow"
	if u < p.p_snow + p.p_cold:
		return "cold"
	return "normal"


static func _price(rng: RandomNumberGenerator, base: float, jitter: float, factor: float) -> int:
	return maxi(1, InnRules.py_round(base * rng.randf_range(1 - jitter, 1 + jitter) * factor))


static func _noble_tier(rng: RandomNumberGenerator, p: Dictionary) -> int:
	var u := rng.randf()
	if u < p.p_noble_high:
		return 2
	if u < p.p_noble_mid:
		return 1
	return 0


static func _weighted(rng: RandomNumberGenerator, weights: Array[float]) -> String:
	var total := 0.0
	for w in weights:
		total += w
	var roll := rng.randf() * total
	for i in weights.size():
		roll -= weights[i]
		if roll < 0.0:
			return KINDS[i]
	return KINDS[KINDS.size() - 1]


static func _news(rng: RandomNumberGenerator, day: int, deal: RunDeal) -> String:
	var topic: String = ["weather", "cheap", "final"][rng.randi_range(0, 2)]
	if topic == "weather" and day < deal.days.size():
		return "weather:%d=%s" % [day + 1, deal.days[day].weather]
	if topic == "cheap":
		for d: DayDeal in deal.days:
			if d.day > day and d.cheap_day:
				return "cheap:%d" % d.day
		return "cheap:none"
	return "final:%s" % deal.final_event
