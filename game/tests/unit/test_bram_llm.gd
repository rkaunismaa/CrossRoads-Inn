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
	var id := llm.ask({"moment": "morning", "day": 1}, "morning_default", [])
	assert_gt(id, 0)
	await wait_for_signal(llm.line_failed, 4)
	assert_signal_emitted(llm, "line_failed")
	assert_signal_not_emitted(llm, "line_ready")


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
