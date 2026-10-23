class_name InnState
extends RefCounted
## The inn's resources. Pure game rules: no nodes, no UI, testable headless.
## Starting values are not set here; they come from balancing (see docs/design.md).

var coins: int
var food: int
var firewood: int


func _init(start_coins: int = 0, start_food: int = 0, start_firewood: int = 0) -> void:
	coins = start_coins
	food = start_food
	firewood = start_firewood
