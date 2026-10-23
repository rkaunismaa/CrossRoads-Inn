extends GutTest


func test_loads_game_params() -> void:
	var r: Dictionary = InnParams.load_json("res://data/params.json")
	assert_true(r.ok, r.error)
	assert_eq(r.params["debt"], 64.0)
	assert_eq(r.params["rooms"], 2.0)


func test_required_keys_match_game_params() -> void:
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://data/params.json"))
	assert_eq(Array(InnParams.REQUIRED_KEYS), data.keys())


func test_missing_file_names_path() -> void:
	var r: Dictionary = InnParams.load_json("res://data/nope.json")
	assert_false(r.ok)
	assert_string_contains(r.error, "nope.json")


func test_bad_json_names_path() -> void:
	var f := FileAccess.open("user://bad.json", FileAccess.WRITE)
	f.store_string("{not json")
	f.close()
	var r: Dictionary = InnParams.load_json("user://bad.json")
	assert_false(r.ok)
	assert_string_contains(r.error, "bad.json")


func test_missing_key_names_it() -> void:
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://data/params.json"))
	data.erase("upkeep")
	var f := FileAccess.open("user://p.json", FileAccess.WRITE)
	f.store_string(JSON.stringify(data))
	f.close()
	var r: Dictionary = InnParams.load_json("user://p.json")
	assert_false(r.ok)
	assert_string_contains(r.error, "upkeep")


func test_non_numeric_value_names_it() -> void:
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://data/params.json"))
	data["rooms"] = "two"
	var f := FileAccess.open("user://p2.json", FileAccess.WRITE)
	f.store_string(JSON.stringify(data))
	f.close()
	var r: Dictionary = InnParams.load_json("user://p2.json")
	assert_false(r.ok)
	assert_string_contains(r.error, "rooms")
