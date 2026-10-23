class_name InnRules
extends RefCounted
## The game rules: a line-for-line port of prototype/inn_sim/rules.py.
## Outcome strings must match Python exactly; the parity test compares ledgers line by line.

## What each kind needs: [room, meal]
const NEEDS := {
	"merchant": [true, true],
	"pilgrim": [false, true],
	"soldier": [true, false],
	"noble": [true, false],
	"wanderer": [false, true],
}


## Python's round(): halves go to the even number (GDScript's round() goes away from zero).
static func py_round(x: float) -> int:
	var f := floorf(x)
	var diff := x - f
	if diff > 0.5:
		return int(f) + 1
	if diff < 0.5:
		return int(f)
	return int(f) if int(f) % 2 == 0 else int(f) + 1


static func describe_news(news: String) -> String:
	var parts := news.split(":", true, 1)
	var topic := parts[0]
	var value := parts[1] if parts.size() > 1 else ""
	if topic == "weather":
		var w := value.split("=", true, 1)
		return "day %s will be %s" % [w[0], w[1]]
	if topic == "cheap":
		return "no cheap firewood days ahead" if value == "none" else "firewood is cheap on day %s" % value
	return "the final night brings: %s" % value.replace("_", " ")


static func new_state(p: Dictionary) -> InnState:
	var s := InnState.new(int(p.start_coins), int(p.start_food), int(p.start_firewood))
	s.goodwill = int(p.start_goodwill)
	return s


static func _add_goodwill(s: InnState, amount: int, p: Dictionary) -> void:
	s.goodwill = clampi(s.goodwill + amount, 0, int(p.goodwill_cap))


static func _with_goodwill(pay: float, s: InnState, p: Dictionary) -> int:
	return py_round(pay * (1 + s.goodwill * p.goodwill_pay_bonus))


static func pay_upkeep(s: InnState, p: Dictionary) -> void:
	var upkeep := int(p.upkeep)
	if s.coins < upkeep:
		s.lost = true
	else:
		s.coins -= upkeep


## Buy as much as coins allow, food first.
static func buy(s: InnState, day: DayDeal, food: int, firewood: int) -> void:
	var food_bought := mini(maxi(0, food), s.coins / day.price_food)
	s.food += food_bought
	s.coins -= food_bought * day.price_food
	var wood_bought := mini(maxi(0, firewood), s.coins / day.price_firewood)
	s.firewood += wood_bought
	s.coins -= wood_bought * day.price_firewood


static func arrivals(s: InnState, day: DayDeal, p: Dictionary) -> int:
	var count := day.base_arrivals
	if s.goodwill >= p.goodwill_arrival_threshold:
		count += 1
	if s.walkout_yesterday:
		count -= 1
	return clampi(count, 0, day.travelers.size())


static func traveler_view(s: InnState, t: DealtTraveler, p: Dictionary) -> TravelerView:
	var v := TravelerView.new()
	v.kind_shown = t.kind
	v.hint = t.hint
	v.needs_room = NEEDS[t.kind][0]
	v.needs_meal = NEEDS[t.kind][1]
	if t.kind == "noble":
		v.offer = int(p.noble_offer)
	elif t.kind == "wanderer":
		v.offer = 0
	else:
		v.offer = _with_goodwill(p["pay_" + t.kind], s, p)
	return v


## Why an action can't be done right now: "" if it can, else "no room", "no food" or "can't haggle".
static func refusal_reason(s: InnState, t: DealtTraveler, action: String, p: Dictionary) -> String:
	if action == "decline":
		return ""
	if action != "accept" and t.kind != "noble":
		return "can't haggle"
	if NEEDS[t.kind][0] and s.occupied >= int(p.rooms):
		return "no room"
	if NEEDS[t.kind][1] and s.food < int(p.food_per_meal):
		return "no food"
	return ""


## Apply one decision. Anything that can't be done counts as a decline.
static func serve(s: InnState, t: DealtTraveler, action: String, p: Dictionary) -> String:
	if action == "decline":
		return "declined"
	var reason := refusal_reason(s, t, action, p)
	if reason != "":
		return "declined (%s)" % reason
	var room: bool = NEEDS[t.kind][0]
	var meal: bool = NEEDS[t.kind][1]
	var pay: int
	if t.kind == "noble" and action != "accept":
		var tier_needed := 1 if action == "haggle_mid" else 2
		if t.noble_tier < tier_needed:
			_add_goodwill(s, -int(p.walkout_goodwill_loss), p)
			s.walkout_yesterday = true
			return "noble walked out"
		pay = int(p.noble_mid if action == "haggle_mid" else p.noble_high)
	else:
		pay = traveler_view(s, t, p).offer
	if room:
		s.occupied += 1
	if meal:
		s.food -= int(p.food_per_meal)
	s.coins += pay
	if t.kind == "pilgrim":
		_add_goodwill(s, int(p.pilgrim_goodwill), p)
	if t.is_thief:
		s.thieves_tonight += 1
	if t.kind == "wanderer" and t.news != "":
		s.news.append(t.news)
		return "accepted +%d, news: %s" % [pay, describe_news(t.news)]
	return "accepted +%d" % pay


static func fire_need(occupied: int, weather: String, p: Dictionary, blizzard := false) -> int:
	var mult: float = {"normal": 1.0, "cold": p.mult_cold, "snow": p.mult_snow}[weather]
	if blizzard:
		mult *= p.blizzard_mult
	return ceili((p.fire_base + p.fire_per_room * occupied) * mult)


## Burn firewood, let thieves steal, then apply the final-night event (final_event "" for none).
static func night(s: InnState, day: DayDeal, p: Dictionary, final_event: String) -> String:
	var notes: PackedStringArray = []
	var need := fire_need(s.occupied, day.weather, p, final_event == "blizzard")
	if s.firewood >= need:
		s.firewood -= need
		notes.append("burned %d firewood" % need)
	else:
		var deficit := need - s.firewood
		s.firewood = 0
		s.coins = maxi(0, s.coins - deficit * int(p.shortage_coin_per_unit))
		_add_goodwill(s, -int(p.shortage_goodwill), p)
		notes.append("short %d firewood" % deficit)
	for i in s.thieves_tonight:
		var stolen := floori(s.coins * p.thief_steal_frac)
		s.coins -= stolen
		notes.append("thief stole %d" % stolen)
	if final_event == "hungry_soldiers":
		var want := int(p.hungry_soldiers_food)
		var short := maxi(0, want - s.food)
		s.food = maxi(0, s.food - want)
		s.coins = maxi(0, s.coins - short * int(p.final_food_penalty))
		notes.append("hungry soldiers, %d food short" % short)
	elif final_event == "robbery":
		if s.goodwill >= p.robbery_safe_goodwill:
			notes.append("robbery stopped by goodwill")
		else:
			var taken := floori(s.coins * p.robbery_frac)
			s.coins -= taken
			notes.append("robbery took %d" % taken)
	elif final_event == "blizzard":
		notes.append("blizzard")
	s.occupied = 0
	s.thieves_tonight = 0
	return ", ".join(notes)
