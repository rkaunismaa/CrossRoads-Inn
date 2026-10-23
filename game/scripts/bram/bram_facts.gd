class_name BramFacts
extends RefCounted
## Builds the facts Bram talks about. Stage 5 feeds these same dictionaries to a local LLM.
##
## Facts hold only what the player could know. Never: is_thief, noble_tier, goodwill, or a
## final event that hasn't been announced (news) or hasn't happened yet.
##
## morning (after DayRunner.begin_day; the UI asks before the player buys):
##   moment "morning", day int, weather String, travelers_coming int,
##   food_low bool              food < travelers_coming * food_per_meal
##   firewood_short_tonight bool firewood < fire_need(all rooms full, today's weather)
##   cheap_firewood bool        today is a cheap firewood day (visible in the price)
##   news Array[String]         news gathered so far, in plain words
##   final_night bool           today is the last day
## traveler (while a traveler is at the counter):
##   moment "traveler", day int, kind String (as shown; a thief shows "merchant"),
##   suspicious bool (Bram's hint), needs_room bool, needs_meal bool, offer int,
##   rooms_full bool, food_low bool (food < meals for everyone still to come)
## night (after DayRunner.end_day, with its notes):
##   moment "night", day int (the day that just ended), shortage bool, theft bool,
##   final_event String ("" unless it happened tonight), coins int, food int, firewood int


static func morning(r: DayRunner, p: Dictionary) -> Dictionary:
	var day := r.day_deal()
	var news: Array[String] = []
	for item in r.state.news:
		news.append(InnRules.describe_news(item))
	return {
		"moment": "morning",
		"day": r.day,
		"weather": day.weather,
		"travelers_coming": r.arrivals_today(),
		"food_low": r.state.food < r.arrivals_today() * int(p.food_per_meal),
		"firewood_short_tonight": r.state.firewood < InnRules.fire_need(int(p.rooms), day.weather, p),
		"cheap_firewood": day.cheap_day,
		"news": news,
		"final_night": r.day == int(p.days),
	}


static func traveler(r: DayRunner, p: Dictionary) -> Dictionary:
	var v := r.current_view()
	return {
		"moment": "traveler",
		"day": r.day,
		"kind": v.kind_shown,
		"suspicious": v.hint,
		"needs_room": v.needs_room,
		"needs_meal": v.needs_meal,
		"offer": v.offer,
		"rooms_full": r.state.occupied >= int(p.rooms),
		"food_low": r.state.food < r.travelers_left() * int(p.food_per_meal),
	}


static func night(r: DayRunner, notes: String, p: Dictionary) -> Dictionary:
	var ended_last_day: bool = r.is_over() and r.result().lost_on_day == 0
	return {
		"moment": "night",
		"day": r.day if r.is_over() else r.day - 1,
		"shortage": notes.contains("short ") and notes.contains("firewood"),
		"theft": notes.contains("thief stole"),
		"final_event": r.deal.final_event if ended_last_day else "",
		"coins": r.state.coins,
		"food": r.state.food,
		"firewood": r.state.firewood,
	}
