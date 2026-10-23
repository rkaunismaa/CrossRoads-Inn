extends GutTest
## Drives the grey-box screen through its buttons, the way a player would.

const MainScene := preload("res://scenes/main.tscn")
var main: Control


func before_each() -> void:
	main = MainScene.instantiate()
	main.llm_config_path = "res://data/no_llm_in_scene_tests.json"  # never reach a live model, however tests are run
	add_child_autofree(main)
	main.start_run(3)


func _node(name: String) -> Node:
	return main.get_node("%" + name)


func _press_whatever_is_visible() -> void:
	if _node("MorningPanel").visible:
		_node("OpenDoors").pressed.emit()
	elif _node("CounterPanel").visible:
		_node("Decline").pressed.emit()
	elif _node("NightPanel").visible:
		_node("Continue").pressed.emit()


func _play_to_end() -> void:
	for i in 300:
		if _node("EndPanel").visible:
			return
		_press_whatever_is_visible()


func test_starts_on_the_morning_panel() -> void:
	assert_true(_node("MorningPanel").visible)
	assert_false(_node("CounterPanel").visible)
	assert_string_contains(_node("TopBar").text, "Coins")
	assert_string_contains(_node("TopBar").text, "Day 1")


func test_full_week_reaches_end_screen() -> void:
	_play_to_end()
	assert_true(_node("EndPanel").visible)
	assert_string_contains(_node("EndText").text, "coins")
	assert_eq(main.runner.ledger[-1].begins_with("End:"), true)


func test_accept_disabled_with_reason_when_rooms_full() -> void:
	_node("OpenDoors").pressed.emit()
	for i in 200:  # find a traveler who needs a room
		if _node("CounterPanel").visible and main.runner.current_view().needs_room:
			break
		_press_whatever_is_visible()
	main.runner.state.occupied = int(main.params.rooms)
	main.refresh_counter()
	assert_true(_node("Accept").disabled)
	assert_eq(_node("Accept").tooltip_text, "no room")


func test_haggle_buttons_only_for_nobles() -> void:
	_node("OpenDoors").pressed.emit()
	for i in 300:
		if _node("CounterPanel").visible:
			var noble: bool = main.runner.current_view().kind_shown == "noble"
			assert_eq(_node("HaggleMid").visible, noble)
			if noble:
				assert_eq(_node("HaggleMid").text, "Haggle: ask %d" % int(main.params.noble_mid))
				assert_eq(_node("HaggleHigh").text, "Haggle: ask %d" % int(main.params.noble_high))
		if _node("EndPanel").visible:
			break
		_press_whatever_is_visible()


func test_buy_spinboxes_cap_to_coins() -> void:
	main.runner.state.coins = 5
	main.runner.day_deal().price_food = 2
	main.runner.day_deal().price_firewood = 2
	main.refresh_market()
	assert_eq(_node("BuyFood").max_value, 2.0)
	_node("BuyFood").value = 2
	assert_eq(_node("BuyFirewood").max_value, 0.0)


func test_play_again_starts_clean() -> void:
	_play_to_end()
	_node("PlayAgain").pressed.emit()
	assert_eq(main.runner.day, 1)
	assert_true(_node("MorningPanel").visible)
	assert_false(_node("EndPanel").visible)
	assert_eq(main.runner.ledger.size(), 0)


func test_missing_params_shows_error() -> void:
	main.params_path = "res://data/nope.json"
	main.start_run(1)
	assert_true(_node("ErrorText").visible)
	assert_string_contains(_node("ErrorText").text, "nope.json")
	assert_false(_node("MorningPanel").visible)


func test_bram_speaks_each_moment() -> void:
	assert_ne(_node("BramBubble").text, "", "morning")
	_node("OpenDoors").pressed.emit()
	if _node("CounterPanel").visible:
		assert_ne(_node("BramBubble").text, "", "traveler")
	while _node("CounterPanel").visible:
		_node("Decline").pressed.emit()
	assert_true(_node("NightPanel").visible)
	assert_ne(_node("BramBubble").text, "", "night")
	assert_string_contains(_node("NightText").text, "firewood")


func test_night_top_bar_shows_the_day_that_just_ended() -> void:
	_node("OpenDoors").pressed.emit()
	while _node("CounterPanel").visible:
		_node("Decline").pressed.emit()
	assert_true(_node("NightPanel").visible)
	assert_string_contains(_node("TopBar").text, "Day 1 of 7 · %s" % main.runner.deal.days[0].weather)


func test_morning_shows_travelers_coming() -> void:
	var n: int = main.runner.arrivals_today()
	assert_string_contains(_node("TopBar").text, "%d travelers today" % n)
	assert_string_contains(_node("Coming").text, "%d travelers" % n)


func test_end_screen_has_week_summary() -> void:
	_play_to_end()
	var text: String = _node("EndText").text
	assert_string_contains(text, "Accepted")
	assert_string_contains(text, "thefts")
	assert_string_contains(text, "cold nights")


func test_counter_top_bar_counts_travelers_still_to_come() -> void:
	_node("OpenDoors").pressed.emit()
	if not _node("CounterPanel").visible:
		pass_test("no travelers today")
		return
	var more: int = main.runner.travelers_left() - 1
	assert_string_contains(_node("TopBar").text, "%d more travelers today" % more)


# --- art (stage 3) ---

func test_traveler_portrait_matches_kind_shown() -> void:
	_node("OpenDoors").pressed.emit()
	if not _node("CounterPanel").visible:
		pass_test("no travelers today")
		return
	var kind: String = main.runner.current_view().kind_shown
	var portrait: TextureRect = _node("TravelerPortrait")
	assert_true(portrait.visible)
	assert_eq(portrait.texture.resource_path, "res://art/%s.png" % kind)


func test_bram_and_backdrop_use_art() -> void:
	assert_eq((_node("BramPortrait") as TextureRect).texture.resource_path, "res://art/bram.png")
	assert_true(_node("Backdrop").visible)
	assert_eq((_node("Backdrop") as TextureRect).texture.resource_path, "res://art/backdrop.png")


func test_missing_art_falls_back_to_grey_boxes() -> void:
	main.art_dir = "res://no_art_here/"
	main.start_run(3)
	assert_false(_node("Backdrop").visible)
	assert_false(_node("BramPortrait").visible)
	_node("OpenDoors").pressed.emit()
	if _node("CounterPanel").visible:
		assert_false(_node("TravelerPortrait").visible)


# --- Bram's LLM voice (stage 5) ---

func test_bram_shows_fixed_line_without_llm() -> void:
	# Unit tests run with CROSSROADS_LLM=off: the fixed line is all there is.
	assert_eq(main.pending_bram_id, -1)
	assert_ne(_node("BramBubble").text, "")


func test_llm_line_replaces_fixed_line() -> void:
	main.pending_bram_id = 42
	main.llm.line_ready.emit(42, "Mind the merchant's purse, friend.")
	assert_eq(_node("BramBubble").text, "Mind the merchant's purse, friend.")


func test_stale_llm_line_is_ignored() -> void:
	var fixed: String = _node("BramBubble").text
	main.pending_bram_id = 42
	main.llm.line_ready.emit(41, "A line for a moment that has passed.")
	assert_eq(_node("BramBubble").text, fixed)


func test_new_moment_drops_the_pending_reply() -> void:
	main.pending_bram_id = 42
	_node("OpenDoors").pressed.emit()
	main.llm.line_ready.emit(42, "Too late now.")
	assert_ne(_node("BramBubble").text, "Too late now.")
