extends Control
## Grey-box screen: the inn counter. Holds no game rules. It only calls DayRunner/InnRules and
## shows what they return, and asks Bram for a line at each moment.
## Built in code so the layout stays readable in one place; stage 3 swaps grey boxes for art.

const GREY_DARK := Color(0.25, 0.25, 0.28)
const GREY := Color(0.45, 0.45, 0.48)
const GREY_LIGHT := Color(0.7, 0.7, 0.72)

var params_path := "res://data/params.json"
var params: Dictionary
var runner: DayRunner
var bram: Bram

var _traveler_box: ColorRect
var _door_x := 0.0
var _rest_x := 0.0


func _ready() -> void:
	_build_ui()
	start_run(randi())


## Start a fresh run: new deal, new state, empty ledger.
func start_run(seed: int) -> void:
	var loaded := InnParams.load_json(params_path)
	_hide_panels()
	if not loaded.ok:
		%ErrorText.text = "Can't start: " + str(loaded.error)
		%ErrorText.visible = true
		%TopBar.text = ""
		%BramBubble.text = ""
		%TravelerBubble.text = ""
		return
	%ErrorText.visible = false
	params = loaded.params
	runner = DayRunner.new(params, Dealer.deal_run(params, seed))
	bram = Bram.new(seed)
	_start_morning()


# --- flow -------------------------------------------------------------------------------------

func _start_morning() -> void:
	_hide_panels()
	if not runner.begin_day():
		_show_end()
		return
	%BuyFood.value = 0
	%BuyFirewood.value = 0
	refresh_market()
	var day := runner.day_deal()
	var cheap := " (cheap today!)" if day.cheap_day else ""
	%Prices.text = "Market: food %d coins, firewood %d coins%s" % [day.price_food, day.price_firewood, cheap]
	var n := runner.arrivals_today()
	%Coming.text = "%d traveler%s coming today." % [n, " is" if n == 1 else "s are"]
	var news := PackedStringArray()
	for item in runner.state.news:
		news.append("• " + InnRules.describe_news(item))
	%NewsList.text = "News:\n" + ("\n".join(news) if news.size() > 0 else "(none yet)")
	%TravelerBubble.text = ""
	_traveler_box.visible = false
	%BramBubble.text = bram.line_for(BramFacts.morning(runner, params))
	%MorningPanel.visible = true
	_refresh_top()


func _on_open_doors() -> void:
	runner.buy(int(%BuyFood.value), int(%BuyFirewood.value))
	%MorningPanel.visible = false
	%Outcome.text = ""
	_next_traveler()


func _next_traveler() -> void:
	_refresh_top()
	if not runner.has_traveler():
		_start_night()
		return
	%CounterPanel.visible = true
	var v := runner.current_view()
	var needs := PackedStringArray()
	if v.needs_room:
		needs.append("a room")
	if v.needs_meal:
		needs.append("a meal")
	var pay := "pays in news" if v.kind_shown == "wanderer" else "offers %d coins" % v.offer
	%TravelerBubble.text = "%s: wants %s, %s" % [v.kind_shown.to_upper(), " and ".join(needs), pay]
	%BramBubble.text = bram.line_for(BramFacts.traveler(runner, params))
	_traveler_box.visible = true
	(_traveler_box.get_child(0) as Label).text = v.kind_shown.to_upper()
	_traveler_box.position.x = _door_x
	create_tween().tween_property(_traveler_box, "position:x", _rest_x, 0.3)
	refresh_counter()


## Enable/disable the decision buttons for the traveler at the counter, with the reason as tooltip.
func refresh_counter() -> void:
	var t := runner.current()
	var v := runner.current_view()
	for pair in [[%Accept, "accept"], [%HaggleMid, "haggle_mid"], [%HaggleHigh, "haggle_high"]]:
		var button: Button = pair[0]
		var reason := InnRules.refusal_reason(runner.state, t, pair[1], params)
		button.disabled = reason != ""
		button.tooltip_text = reason
	var noble := v.kind_shown == "noble"
	%HaggleMid.visible = noble
	%HaggleHigh.visible = noble
	%HaggleMid.text = "Haggle: ask %d" % int(params.noble_mid)
	%HaggleHigh.text = "Haggle: ask %d" % int(params.noble_high)
	var left := runner.travelers_left() - 1
	%TravelersLeft.text = "%d more traveler%s today" % [left, "" if left == 1 else "s"]
	_refresh_top()


func _decide(action: String) -> void:
	%Outcome.text = "Last: %s -> %s" % [runner.current_view().kind_shown, runner.decide(action)]
	_next_traveler()


func _start_night() -> void:
	%CounterPanel.visible = false
	_traveler_box.visible = false
	%TravelerBubble.text = ""
	var notes := runner.end_day()
	%NightPanel.visible = true
	var day_lines := PackedStringArray()
	for line in runner.ledger:
		if line.begins_with("Day %d slot" % _shown_day()):
			day_lines.append(line.split(": ", true, 1)[1])
	%NightText.text = "Tonight: %s\n\nToday:\n%s" % [notes, "\n".join(day_lines) if day_lines.size() > 0 else "(no travelers)"]
	%BramBubble.text = bram.line_for(BramFacts.night(runner, notes, params))
	_refresh_top()


func _on_continue() -> void:
	if runner.is_over():
		_show_end()
	else:
		_start_morning()


func _show_end() -> void:
	_hide_panels()
	var r := runner.result()
	var debt := int(params.debt)
	if r.lost_on_day > 0:
		%EndText.text = "You lost on day %d: couldn't pay the upkeep.\nYou had %d coins." % [r.lost_on_day, r.end_coins]
	else:
		%EndText.text = "%s\nYou ended the week with %d coins; the landlord wanted %d." % [
			"You kept the inn!" if r.won else "You couldn't pay the landlord.", r.end_coins, debt]
	%EndText.text += "\n\n" + _week_summary()
	%EndPanel.visible = true
	_refresh_top()


## A few totals from the ledger, for the end screen.
func _week_summary() -> String:
	var accepted := 0
	var thefts := 0
	var cold_nights := 0
	for line in runner.ledger:
		if line.contains(" slot ") and line.contains(": accepted"):
			accepted += 1
		thefts += line.count("thief stole")
		if line.contains(" night: short "):
			cold_nights += 1
	var summary := "Accepted %d travelers · %d thefts · %d cold nights" % [accepted, thefts, cold_nights]
	if runner.result().lost_on_day == 0:
		summary += "\nFinal night: %s" % runner.deal.final_event.replace("_", " ")
	return summary


# --- display helpers --------------------------------------------------------------------------

## Cap the buy controls to what the coins allow, food first (as the rules buy).
func refresh_market() -> void:
	var day := runner.day_deal()
	%BuyFood.max_value = runner.state.coins / day.price_food
	_on_food_changed(%BuyFood.value)


func _on_food_changed(_value: float) -> void:
	if runner == null:
		return
	var day := runner.day_deal()
	var left := runner.state.coins - int(%BuyFood.value) * day.price_food
	%BuyFirewood.max_value = maxi(0, left / day.price_firewood)


func _refresh_top() -> void:
	var s := runner.state
	var day := runner.deal.days[_shown_day() - 1]
	%TopBar.text = "Coins %d   Food %d   Firewood %d   Rooms %d/%d   Day %d of %d · %s" % [
		s.coins, s.food, s.firewood, s.occupied, int(params.rooms), day.day, int(params.days), day.weather]
	if %MorningPanel.visible:
		%TopBar.text += "   · %d travelers today" % runner.arrivals_today()
	elif %CounterPanel.visible:
		%TopBar.text += "   · %d more travelers today" % maxi(0, runner.travelers_left() - 1)


## The day the screen is about: during the night summary that's the day just ended.
func _shown_day() -> int:
	return runner.day - 1 if %NightPanel.visible and not runner.is_over() else runner.day


func _hide_panels() -> void:
	for panel in [%MorningPanel, %CounterPanel, %NightPanel, %EndPanel]:
		panel.visible = false


# --- layout -----------------------------------------------------------------------------------

func _named(node: Node, unique: String) -> Node:
	node.name = unique
	node.unique_name_in_owner = true
	return node


func _own(node: Node) -> void:
	node.owner = self
	for child in node.get_children():
		_own(child)


func _label(unique: String, text := "") -> Label:
	var l: Label = _named(Label.new(), unique)
	l.text = text
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	return l


func _button(unique: String, text: String, on_press: Callable) -> Button:
	var b: Button = _named(Button.new(), unique)
	b.text = text
	b.pressed.connect(on_press)
	return b


func _box(color: Color, size: Vector2, caption: String) -> ColorRect:
	var r := ColorRect.new()
	r.color = color
	r.custom_minimum_size = size
	var l := Label.new()
	l.text = caption
	l.set_anchors_preset(Control.PRESET_FULL_RECT)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	r.add_child(l)
	return r


func _bubble(unique: String) -> Label:
	var l := _label(unique)
	l.custom_minimum_size = Vector2(260, 60)
	l.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
	return l


func _build_ui() -> void:
	var bg := ColorRect.new()
	bg.color = GREY_DARK.darkened(0.4)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)

	var margin := MarginContainer.new()
	margin.set_anchors_preset(Control.PRESET_FULL_RECT)
	for side in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 16)
	add_child(margin)
	var root := VBoxContainer.new()
	root.add_theme_constant_override("separation", 12)
	margin.add_child(root)

	root.add_child(_label("TopBar"))
	root.add_child(_label("ErrorText"))

	# The scene: door, traveler (with bubble), counter, Bram (with bubble).
	var scene := Control.new()
	scene.custom_minimum_size = Vector2(1200, 300)
	root.add_child(scene)
	var door := _box(GREY, Vector2(90, 180), "door")
	door.position = Vector2(20, 100)
	scene.add_child(door)
	_door_x = 20.0
	_rest_x = 300.0
	_traveler_box = _box(GREY_LIGHT, Vector2(90, 150), "")
	_traveler_box.position = Vector2(_rest_x, 130)
	scene.add_child(_traveler_box)
	var tb := _bubble("TravelerBubble")
	tb.position = Vector2(220, 20)
	scene.add_child(tb)
	var counter := _box(GREY, Vector2(380, 70), "counter")
	counter.position = Vector2(440, 210)
	scene.add_child(counter)
	var bram_box := _box(GREY_LIGHT, Vector2(90, 150), "BRAM")
	bram_box.position = Vector2(880, 130)
	scene.add_child(bram_box)
	var bb := _bubble("BramBubble")
	bb.position = Vector2(820, 20)
	bb.custom_minimum_size = Vector2(360, 60)
	scene.add_child(bb)

	# Morning: prices, news, buying, then open the doors.
	var morning: VBoxContainer = _named(VBoxContainer.new(), "MorningPanel")
	morning.add_child(_label("Prices"))
	morning.add_child(_label("Coming"))
	morning.add_child(_label("NewsList"))
	var buys := HBoxContainer.new()
	for pair in [["BuyFood", "Buy food:"], ["BuyFirewood", "Buy firewood:"]]:
		var l := Label.new()
		l.text = pair[1]
		buys.add_child(l)
		var spin: SpinBox = _named(SpinBox.new(), pair[0])
		spin.min_value = 0
		buys.add_child(spin)
	morning.add_child(buys)
	morning.add_child(_button("OpenDoors", "Open the doors", _on_open_doors))
	root.add_child(morning)

	# Counter: decisions for the traveler in front of you.
	var counter_panel: VBoxContainer = _named(VBoxContainer.new(), "CounterPanel")
	var buttons := HBoxContainer.new()
	buttons.add_child(_button("Accept", "Accept", _decide.bind("accept")))
	buttons.add_child(_button("Decline", "Decline", _decide.bind("decline")))
	buttons.add_child(_button("HaggleMid", "Haggle", _decide.bind("haggle_mid")))
	buttons.add_child(_button("HaggleHigh", "Haggle", _decide.bind("haggle_high")))
	counter_panel.add_child(buttons)
	counter_panel.add_child(_label("TravelersLeft"))
	counter_panel.add_child(_label("Outcome"))
	root.add_child(counter_panel)

	# Night summary, then on to the next morning.
	var night: VBoxContainer = _named(VBoxContainer.new(), "NightPanel")
	night.add_child(_label("NightText"))
	night.add_child(_button("Continue", "Continue", _on_continue))
	root.add_child(night)

	# End of the week.
	var end: VBoxContainer = _named(VBoxContainer.new(), "EndPanel")
	end.add_child(_label("EndText"))
	end.add_child(_button("PlayAgain", "Play again", func() -> void: start_run(randi())))
	root.add_child(end)

	_own(bg)
	_own(margin)
	(%BuyFood as SpinBox).value_changed.connect(_on_food_changed)
