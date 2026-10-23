extends GutTest
## The LLM client must never block or break the game: failures are quiet and the fixed line stays.

var llm: BramLLM


func before_each() -> void:
	llm = BramLLM.new()
	add_child_autofree(llm)


func test_config_loads_and_env_can_switch_it_off() -> void:
	llm.load_config("res://data/bram_llm.json")
	assert_eq(llm.model, "qwen3:4b-instruct")
	# tools/run-tests.sh sets CROSSROADS_LLM=off so unit tests never depend on a running model.
	assert_eq(llm.enabled, OS.get_environment("CROSSROADS_LLM") != "off")


func test_disabled_client_does_not_ask() -> void:
	llm.enabled = false
	assert_eq(llm.ask({"moment": "morning"}, "morning_default", []), -1)


func test_unreachable_server_fails_quietly() -> void:
	llm.enabled = true
	llm.url = "http://127.0.0.1:9/api/chat"  # discard port: nothing listens
	llm.timeout_s = 2.0
	watch_signals(llm)
	var morning := {"moment": "morning", "day": 1, "weather": "normal", "travelers_coming": 3, "food_low": false,
		"firewood_short_tonight": false, "cheap_firewood": false, "news": [], "final_night": false}
	assert_true(BramVoice.check_facts(morning).ok, "the test must reach the network, not stop at the schema")
	llm.warm = true  # skip the long cold-start timeout
	var id := llm.ask(morning, "morning_default", [])
	assert_gt(id, 0)
	await wait_for_signal(llm.line_failed, 4)
	assert_signal_emitted(llm, "line_failed")
	assert_signal_not_emitted(llm, "line_ready")
	var params: Array = get_signal_parameters(llm, "line_failed")
	assert_string_starts_with(str(params[1]), "no answer")


func test_live_model_answers_in_character() -> void:
	if OS.get_environment("CROSSROADS_LLM_LIVE") != "1":
		pass_test("set CROSSROADS_LLM_LIVE=1 to run against the real model")
		return
	llm.load_config("res://data/bram_llm.json")
	llm.enabled = true
	llm.timeout_s = 30.0  # the first call loads the model
	watch_signals(llm)
	var facts := {"moment": "traveler", "day": 2, "kind": "merchant", "suspicious": true, "needs_room": true,
		"needs_meal": true, "offer": 8, "rooms_full": false, "food_low": false}
	llm.ask(facts, "traveler_suspicious", Bram.LINES["traveler_suspicious"])
	await wait_for_signal(llm.line_ready, 35)
	assert_signal_emitted(llm, "line_ready")


func test_cold_requests_get_a_long_timeout_until_the_model_answers() -> void:
	llm.enabled = true
	llm.url = "http://127.0.0.1:9/api/chat"
	llm.timeout_s = 4.0
	var morning := {"moment": "morning", "day": 1, "weather": "normal", "travelers_coming": 3, "food_low": false,
		"firewood_short_tonight": false, "cheap_firewood": false, "news": [], "final_night": false}
	assert_false(llm.warm)
	llm.ask(morning, "morning_default", [])
	assert_eq(_last_request().timeout, BramLLM.COLD_TIMEOUT_S, "first load of the model can take a while")
	llm.warm = true
	llm.ask(morning, "morning_default", [])
	assert_eq(_last_request().timeout, 4.0)


func test_warm_up_asks_the_model_to_load() -> void:
	llm.enabled = true
	llm.url = "http://127.0.0.1:9/api/chat"
	llm.warm_up()
	assert_eq(_last_request().timeout, BramLLM.COLD_TIMEOUT_S)


func _last_request() -> HTTPRequest:
	var found: HTTPRequest = null
	for child in llm.get_children():
		if child is HTTPRequest:
			found = child
	return found
