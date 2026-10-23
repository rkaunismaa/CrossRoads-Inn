extends Control
## Grey-box UI. Reads from InnState; never holds game rules itself.

var inn: InnState = InnState.new()

@onready var stock_label: Label = %StockLabel


func _ready() -> void:
	_refresh()


func _refresh() -> void:
	stock_label.text = "Coins: %d   Food: %d   Firewood: %d" % [inn.coins, inn.food, inn.firewood]
