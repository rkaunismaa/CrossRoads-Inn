extends SceneTree
## Writes THIRD_PARTY_NOTICES.txt for a release build (called by tools/export-linux.sh).
##   godot --headless --path game --script res://tools/write_notices.gd -- <output file>

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	if args.is_empty():
		push_error("usage: -- <output file>")
		quit(1)
		return
	var lines := PackedStringArray([
		"Crossroads Inn - third-party notices", "",
		"== Godot Engine ==", Engine.get_license_text(), "",
		"== Godot Engine third-party components ==",
	])
	for info: Dictionary in Engine.get_copyright_info():
		lines.append("- %s" % info.name)
	lines.append_array(["", "== Generated art ==",
		"All images in this game were generated with Stable Diffusion XL base 1.0 (Stability AI),",
		"licensed under the CreativeML Open RAIL++-M License. Prompts and seeds: art/provenance.json in the source repository.", "",
		"== Bram's optional dialogue model ==",
		"If Ollama is installed on the player's machine, Bram's lines may be phrased locally by",
		"Qwen3-4B Instruct (Apache License 2.0). The model is not included with this game."])
	var f := FileAccess.open(args[0], FileAccess.WRITE)
	f.store_string("\n".join(lines) + "\n")
	f.close()
	quit(0)
