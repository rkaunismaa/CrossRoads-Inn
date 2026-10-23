class_name Bram
extends RefCounted
## Bram, the recurring NPC who chats with the player. For now he picks hand-written lines from the
## facts (BramFacts); stage 5 swaps this for a local LLM. He only reads facts and returns text:
## he never sees the InnState and never changes the game.

## Lines may use {key} placeholders filled from the facts.
const LINES := {
	"morning_final_night": [
		"Last night of the week. Whatever comes tonight, we face it with what's in the stores.",
		"Day {day}, the last one. The landlord comes at dawn, and something always goes wrong on the final night.",
	],
	"morning_firewood_short": [
		"The woodpile's thin. A full house tonight would leave us cold.",
		"Not enough firewood for every room tonight. The market has some, for a price.",
	],
	"morning_food_low": [
		"{travelers_coming} coming today and the larder won't feed them all.",
		"We're short on food for today's crowd. Buy some, or turn hungry folk away.",
	],
	"morning_snow": [
		"Snow on the road. Every hearth will eat more wood tonight.",
		"Snowing. Travelers will want warm rooms, and warm rooms want firewood.",
	],
	"morning_cheap_firewood": [
		"Firewood's cheap in the village today. Might be worth stocking up.",
		"The woodcutter's practically giving it away today.",
	],
	"morning_default": [
		"Day {day}, {weather} weather. {travelers_coming} on the road, by the look of it.",
		"Morning. {travelers_coming} travelers should pass through today.",
	],
	"traveler_suspicious": [
		"Watch that one's purse... and yours.",
		"Fine clothes, shifty eyes. I don't like it.",
		"Something about this merchant doesn't sit right with me.",
	],
	"traveler_rooms_full": [
		"Every room's taken. Unless you want them sleeping on the bar.",
		"We're full up. Nowhere to put this one.",
	],
	"traveler_merchant": [
		"A merchant. {offer} coins for a bed and a meal is good money.",
		"Merchants pay well. This one looks honest enough.",
	],
	"traveler_pilgrim": [
		"A pilgrim. They pay little, but word of kindness travels.",
		"Feed a pilgrim and the road remembers it.",
	],
	"traveler_soldier": [
		"A soldier wanting a warm room. {offer} coins, if the woodpile can take it.",
		"Soldiers pay fair, but a room means a lit hearth tonight.",
	],
	"traveler_noble": [
		"A noble, offering {offer}. He can afford more. Push, but not too hard.",
		"Nobles open low. Ask for more, but if he storms out, folk will talk.",
	],
	"traveler_wanderer": [
		"A wanderer. No coin, but they always know what's coming down the road.",
		"Feed the wanderer. News is worth more than coins some days.",
	],
	"traveler_default": [
		"Another traveler. Your call.",
		"Someone at the door.",
	],
	"night_theft": [
		"Coins missing from the till. I knew that merchant was trouble.",
		"We've been robbed in the night. Should've listened to me.",
	],
	"night_shortage": [
		"The hearths went cold. Guests won't forget that.",
		"Ran out of firewood. Cost us coins and good will.",
	],
	"night_final_event": [
		"What a night. The {final_event} is behind us, at least.",
		"So that was the last night: {final_event}. Let's count what's left.",
	],
	"night_default": [
		"Quiet night. {coins} coins in the till.",
		"All warm, all fed. {coins} coins, {food} food, {firewood} firewood left.",
	],
}

var _rng := RandomNumberGenerator.new()


func _init(seed: int = 0) -> void:
	_rng.seed = seed


## Which group of lines fits these facts, by priority.
static func situation_for(facts: Dictionary) -> String:
	match facts.get("moment", ""):
		"morning":
			if facts.final_night:
				return "morning_final_night"
			if facts.firewood_short_tonight:
				return "morning_firewood_short"
			if facts.food_low:
				return "morning_food_low"
			if facts.weather == "snow":
				return "morning_snow"
			if facts.cheap_firewood:
				return "morning_cheap_firewood"
			return "morning_default"
		"traveler":
			if facts.suspicious:
				return "traveler_suspicious"
			if facts.rooms_full and facts.needs_room:
				return "traveler_rooms_full"
			var per_kind := "traveler_" + str(facts.kind)
			return per_kind if LINES.has(per_kind) else "traveler_default"
		"night":
			if facts.theft:
				return "night_theft"
			if facts.shortage:
				return "night_shortage"
			if facts.final_event != "":
				return "night_final_event"
			return "night_default"
	return "traveler_default"


func line_for(facts: Dictionary) -> String:
	var options: Array = LINES[situation_for(facts)]
	return _fill(options[_rng.randi_range(0, options.size() - 1)], facts)


## All of this situation's fixed lines, filled in: the LLM uses them as examples of Bram's voice.
static func examples_for(facts: Dictionary) -> Array[String]:
	var out: Array[String] = []
	for line: String in LINES[situation_for(facts)]:
		out.append(_fill(line, facts))
	return out


static func _fill(line: String, facts: Dictionary) -> String:
	var fill := facts.duplicate()
	if fill.has("final_event"):
		fill.final_event = str(fill.final_event).replace("_", " ")
	return line.format(fill)
