class_name RunDeal
extends RefCounted
## A whole dealt run: every random outcome, decided before play starts.

var seed: int
var final_event: String
var days: Array[DayDeal] = []


## Builds a RunDeal from the JSON shape written by `python3 -m inn_sim export-fixtures`.
static func from_dict(d: Dictionary) -> RunDeal:
	var deal := RunDeal.new()
	deal.seed = int(d.seed)
	deal.final_event = str(d.final_event)
	for dd: Dictionary in d.days:
		var day := DayDeal.new()
		day.day = int(dd.day)
		day.weather = str(dd.weather)
		day.price_food = int(dd.price_food)
		day.price_firewood = int(dd.price_firewood)
		day.cheap_day = bool(dd.cheap_day)
		day.base_arrivals = int(dd.base_arrivals)
		for t: Dictionary in dd.travelers:
			var news: String = "" if t.news == null else str(t.news)
			day.travelers.append(DealtTraveler.new(str(t.kind), bool(t.is_thief), bool(t.hint), int(t.noble_tier), news))
		deal.days.append(day)
	return deal
