class_name BramLLM
extends Node
## Asks a local LLM (Ollama) to phrase Bram's line. Never blocks the game and fails quietly:
## the caller shows Bram's fixed line first and only swaps in a reply from line_ready.
## Bram's text never feeds back into the game state.

signal line_ready(id: int, text: String)
signal line_failed(id: int, reason: String)

## Loading the model on first use can take seconds (longer from a cold disk or on CPU). Giving up
## early makes Ollama abandon the load, so requests wait this long until the model has answered once.
const COLD_TIMEOUT_S := 60.0

var enabled := false
var url := ""
var model := ""
var timeout_s := 4.0
var temperature := 0.9
var max_words := 30
var warm := false  ## true once the model has answered: then requests use the short timeout_s
var check_facts := true  ## only game/tools/bram_eval.gd turns this off, to measure the model on its own

var _next_id := 1


## Load settings from JSON. CROSSROADS_LLM=off in the environment switches the LLM off (used by tests).
func load_config(path: String) -> void:
	if not FileAccess.file_exists(path):
		enabled = false
		return
	var cfg: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if typeof(cfg) != TYPE_DICTIONARY:
		enabled = false
		return
	url = str(cfg.get("url", ""))
	model = str(cfg.get("model", ""))
	timeout_s = float(cfg.get("timeout_s", 4.0))
	temperature = float(cfg.get("temperature", 0.9))
	max_words = int(cfg.get("max_words", 30))
	enabled = bool(cfg.get("enabled", false)) and OS.get_environment("CROSSROADS_LLM") != "off"


## Ask for a line. Returns a request id (-1 when disabled); the answer arrives as line_ready or line_failed.
## check_against: facts to check the reply against, if not the ones sent (only game/tools/bram_eval.gd uses it,
## so injected text in the facts can't make its own words look allowed).
func ask(facts: Dictionary, situation: String, examples: Array, check_against: Dictionary = {}) -> int:
	if not enabled:
		return -1
	var id := _next_id
	_next_id += 1
	var checked := BramVoice.check_facts(facts) if check_facts else {"ok": true}
	if not checked.ok:
		line_failed.emit.call_deferred(id, "facts failed the check: " + checked.reason)
		return id
	var http := HTTPRequest.new()
	http.timeout = timeout_s if warm else COLD_TIMEOUT_S
	add_child(http)
	var cfg := {"model": model, "temperature": temperature}
	var body := BramVoice.build_request(facts.duplicate(true), situation, examples, cfg, id)
	var reply_facts := check_against if not check_against.is_empty() else facts
	http.request_completed.connect(_on_done.bind(http, id, reply_facts.duplicate(true)))
	var err := http.request(url, ["Content-Type: application/json"], HTTPClient.METHOD_POST, JSON.stringify(body))
	if err != OK:
		http.queue_free()
		line_failed.emit.call_deferred(id, "request error %d" % err)
	return id


## Ask Ollama to load the model now, so the first line in play isn't the one that waits for it.
func warm_up() -> void:
	if not enabled:
		return
	var http := HTTPRequest.new()
	http.timeout = COLD_TIMEOUT_S
	add_child(http)
	http.request_completed.connect(func(result: int, code: int, _h: PackedStringArray, _b: PackedByteArray) -> void:
		http.queue_free()
		if result == HTTPRequest.RESULT_SUCCESS and code == 200:
			warm = true)
	var body := {"model": model, "messages": [], "keep_alive": "30m"}
	if http.request(url, ["Content-Type: application/json"], HTTPClient.METHOD_POST, JSON.stringify(body)) != OK:
		http.queue_free()


func _on_done(result: int, code: int, _headers: PackedStringArray, body: PackedByteArray,
		http: HTTPRequest, id: int, facts: Dictionary) -> void:
	http.queue_free()
	if result != HTTPRequest.RESULT_SUCCESS or code != 200:
		line_failed.emit(id, "no answer (result %d, http %d)" % [result, code])
		return
	var json := JSON.new()
	if json.parse(body.get_string_from_utf8()) != OK or typeof(json.data) != TYPE_DICTIONARY:
		line_failed.emit(id, "unreadable answer")
		return
	warm = true
	var content := str(json.data.get("message", {}).get("content", ""))
	var checked := BramVoice.clean_and_check(content, facts, max_words)
	if checked.ok:
		line_ready.emit(id, checked.text)
	else:
		line_failed.emit(id, "rejected: %s: %s" % [checked.reason, content.strip_edges().substr(0, 100)])
