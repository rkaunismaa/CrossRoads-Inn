extends SceneTree
## Writes THIRD_PARTY_NOTICES.txt for a release build (called by tools/export-linux.sh).
##   godot --headless --path game --script res://tools/write_notices.gd -- <output file>
## Includes every Godot component's copyright lines and licence, then the full text of each licence,
## as Godot's "Complying with licenses" guidance asks.

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	if args.is_empty():
		printerr("usage: -- <output file>")
		quit(1)
		return
	var lines := PackedStringArray([
		"Crossroads Inn - third-party notices", "",
		"== Godot Engine (MIT License) ==", Engine.get_license_text(), "",
		"== Third-party components in Godot Engine ==", ""])
	for info: Dictionary in Engine.get_copyright_info():
		lines.append(str(info.name))
		for part: Dictionary in info.parts:
			for holder in part.copyright:
				lines.append("  Copyright: " + str(holder))
			lines.append("  License: " + str(part.license))
		lines.append("")
	lines.append_array(["== Licence texts ==", ""])
	var licenses := Engine.get_license_info()
	for name: String in licenses:
		lines.append_array(["--- " + name + " ---", str(licenses[name]), ""])
	lines.append_array(["== Generated art ==",
		"The images in this game were generated with Stable Diffusion XL base 1.0 by Stability AI",
		"(the model is licensed under the CreativeML Open RAIL++-M License).", "",
		"== Bram's optional dialogue model ==",
		"If the player turns on \"Bram's local AI voice\" and has Ollama installed, Bram's lines may be phrased",
		"on the player's computer by Qwen3-4B Instruct (Apache License 2.0). The model is not included with this game."])
	var f := FileAccess.open(args[0], FileAccess.WRITE)
	if f == null:
		printerr("cannot write %s: %s" % [args[0], error_string(FileAccess.get_open_error())])
		quit(1)
		return
	f.store_string("\n".join(lines) + "\n")
	f.close()
	quit(0)
