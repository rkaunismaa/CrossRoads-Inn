class_name BramLLM
extends Node
## Asks a local LLM (Ollama) to phrase Bram's line. Never blocks the game and fails quietly:
## the caller shows Bram's fixed line first and only swaps in a reply from line_ready.
## Bram's text never feeds back into the game state.

signal line_ready(id: int, text: String)
signal line_failed(id: int, reason: String)

var enabled := false
var url := ""
var model := ""
var timeout_s := 4.0
var temperature := 0.9
var max_words := 30

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
func ask(facts: Dictionary, situation: String, examples: Array) -> int:
	if not enabled:
		return -1
	var id := _next_id
	_next_id += 1
	var http := HTTPRequest.new()
	http.timeout = timeout_s
	add_child(http)
	var cfg := {"model": model, "temperature": temperature}
	var body := BramVoice.build_request(facts.duplicate(true), situation, examples, cfg, id)
	http.request_completed.connect(_on_done.bind(http, id, facts.duplicate(true)))
	var err := http.request(url, ["Content-Type: application/json"], HTTPClient.METHOD_POST, JSON.stringify(body))
	if err != OK:
		http.queue_free()
		line_failed.emit.call_deferred(id, "request error %d" % err)
	return id


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
	var content := str(json.data.get("message", {}).get("content", ""))
	var checked := BramVoice.clean_and_check(content, facts, max_words)
	if checked.ok:
		line_ready.emit(id, checked.text)
	else:
		line_failed.emit(id, "rejected: " + checked.reason)
