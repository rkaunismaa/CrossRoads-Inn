extends GutTest
## The GDScript rules must reproduce the Python simulation's ledger exactly, for every exported fixture.
## Regenerate fixtures after re-tuning: cd prototype && python3 -m inn_sim export-fixtures


func _fixture(name: String) -> Dictionary:
	return JSON.parse_string(FileAccess.get_file_as_string("res://tests/fixtures/" + name))


## Drive a DayRunner the way the UI does, using the fixture's recorded decisions.
func _play(runner: DayRunner, f: Dictionary) -> void:
	var decisions := {}
	for d: Array in f.decisions:
		decisions[Vector2i(int(d[0]), int(d[1]))] = str(d[2])
	while not runner.is_over():
		if not runner.begin_day():
			break
		var buys: Array = f.market.get(str(runner.day), [0, 0])
		runner.buy(int(buys[0]), int(buys[1]))
		while runner.has_traveler():
			runner.decide(decisions.get(Vector2i(runner.day, runner.slot()), "decline"))
		runner.end_day()


func test_every_fixture_matches_python() -> void:
	var checked := 0
	for name in DirAccess.get_files_at("res://tests/fixtures"):
		if not name.ends_with(".json") or name == "manifest.json":
			continue
		var f := _fixture(name)
		var runner := DayRunner.new(f.params, RunDeal.from_dict(f.deal))
		_play(runner, f)
		var expected: Array = f.ledger
		var got := Array(runner.ledger)
		for i in mini(got.size(), expected.size()):
			if got[i] != expected[i]:
				fail_test("%s: first difference at line %d:\n  godot:  %s\n  python: %s" % [name, i + 1, got[i], expected[i]])
				break
		assert_eq(got.size(), expected.size(), name + " ledger length")
		assert_eq(runner.result().end_coins, int(f.result.end_coins), name + " end coins")
		assert_eq(runner.result().won, bool(f.result.won), name + " won")
		checked += 1
	assert_gte(checked, 20)


func test_buy_caps_to_coins() -> void:
	var f := _fixture("careful_0.json")
	var runner := DayRunner.new(f.params, RunDeal.from_dict(f.deal))
	runner.begin_day()
	runner.state.coins = 5
	var day := runner.day_deal()
	day.price_food = 2
	day.price_firewood = 2
	var food: int = runner.state.food
	var wood: int = runner.state.firewood
	runner.buy(2, 2)
	assert_eq([runner.state.food - food, runner.state.firewood - wood, runner.state.coins], [2, 0, 1])


func test_runner_steps_through_a_day() -> void:
	var f := _fixture("careful_0.json")
	var runner := DayRunner.new(f.params, RunDeal.from_dict(f.deal))
	assert_eq(runner.day, 1)
	assert_true(runner.begin_day())
	runner.buy(0, 0)
	var n := runner.arrivals_today()
	assert_eq(runner.travelers_left(), n)
	runner.decide("decline")
	assert_eq(runner.travelers_left(), n - 1)
	while runner.has_traveler():
		runner.decide("decline")
	assert_string_contains(runner.end_day(), "firewood")
	assert_eq(runner.day, 2)
	assert_false(runner.is_over())
