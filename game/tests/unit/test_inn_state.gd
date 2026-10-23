extends GutTest


func test_new_inn_holds_starting_resources() -> void:
	var inn := InnState.new(10, 5, 3)
	assert_eq(inn.coins, 10)
	assert_eq(inn.food, 5)
	assert_eq(inn.firewood, 3)


func test_default_inn_is_empty() -> void:
	var inn := InnState.new()
	assert_eq(inn.coins, 0)
	assert_eq(inn.food, 0)
	assert_eq(inn.firewood, 0)
