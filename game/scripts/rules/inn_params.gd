class_name InnParams
extends RefCounted
## Loads the tuned numbers from params.json (written by `python3 -m inn_sim export`).
## No balance number is ever hard-coded in GDScript; they all come from here.

const REQUIRED_KEYS: PackedStringArray = ["start_coins", "start_food", "start_firewood", "start_goodwill", "days", "debt", "upkeep", "rooms", "price_food", "price_firewood", "price_jitter", "p_cheap_day", "cheap_discount", "p_cold", "p_snow", "fire_base", "fire_per_room", "mult_cold", "mult_snow", "blizzard_mult", "shortage_coin_per_unit", "shortage_goodwill", "travelers_min", "travelers_max", "goodwill_arrival_threshold", "w_merchant", "w_pilgrim", "w_soldier", "w_noble", "w_wanderer", "thief_p", "pay_merchant", "pay_pilgrim", "pilgrim_goodwill", "pay_soldier", "food_per_meal", "goodwill_pay_bonus", "goodwill_cap", "hint_accuracy", "hint_false_pos", "thief_steal_frac", "noble_offer", "noble_mid", "noble_high", "p_noble_mid", "p_noble_high", "walkout_goodwill_loss", "hungry_soldiers_food", "final_food_penalty", "robbery_frac", "robbery_safe_goodwill"]


## Returns {"ok": bool, "params": Dictionary, "error": String}. Values are floats.
static func load_json(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return _fail("params file not found: %s (run: cd prototype && python3 -m inn_sim export)" % path)
	var json := JSON.new()  # parse() reports errors quietly, unlike JSON.parse_string()
	if json.parse(FileAccess.get_file_as_string(path)) != OK:
		return _fail("params file is not valid JSON: %s (line %d: %s)" % [path, json.get_error_line(), json.get_error_message()])
	var data: Variant = json.data
	if typeof(data) != TYPE_DICTIONARY:
		return _fail("params file is not a JSON object: %s" % path)
	var params := {}
	for key in REQUIRED_KEYS:
		if not data.has(key):
			return _fail("params file %s is missing \"%s\" (re-run the export)" % [path, key])
		var value: Variant = data[key]
		if typeof(value) != TYPE_FLOAT and typeof(value) != TYPE_INT:
			return _fail("param \"%s\" in %s is not a number: %s" % [key, path, str(value)])
		params[key] = float(value)
	return {"ok": true, "params": params, "error": ""}


static func _fail(message: String) -> Dictionary:
	return {"ok": false, "params": {}, "error": message}
