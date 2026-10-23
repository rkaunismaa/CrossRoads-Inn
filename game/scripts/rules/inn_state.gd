class_name InnState
extends RefCounted
## The inn's state during a run. Pure game rules: no nodes, no UI, testable headless.
## Starting values come from params.json via InnRules.new_state().

var coins: int
var food: int
var firewood: int
var goodwill: int = 0  ## hidden from the player
var occupied: int = 0
var thieves_tonight: int = 0
var walkout_yesterday: bool = false  ## a noble walked out; costs one arrival the next day
var lost: bool = false
var news: PackedStringArray = []


func _init(start_coins: int = 0, start_food: int = 0, start_firewood: int = 0) -> void:
	coins = start_coins
	food = start_food
	firewood = start_firewood


## A copy of every field, used to prove that reading the state (e.g. by Bram) changes nothing.
func snapshot() -> Dictionary:
	return {
		"coins": coins, "food": food, "firewood": firewood, "goodwill": goodwill, "occupied": occupied,
		"thieves_tonight": thieves_tonight, "walkout_yesterday": walkout_yesterday, "lost": lost,
		"news": Array(news.duplicate()),
	}
