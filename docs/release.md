# Releasing a Linux build

## One-time setup: export templates

Godot needs its export templates to build. They must match the editor version (4.7.2).

```bash
curl -LO https://github.com/godotengine/godot/releases/download/4.7.2-stable/Godot_v4.7.2-stable_export_templates.tpz
curl -LO https://github.com/godotengine/godot/releases/download/4.7.2-stable/SHA512-SUMS.txt
grep " Godot_v4.7.2-stable_export_templates.tpz$" SHA512-SUMS.txt | sha512sum -c
mkdir -p ~/.local/share/godot/export_templates/4.7.2.stable
unzip -j Godot_v4.7.2-stable_export_templates.tpz 'templates/version.txt' 'templates/linux_*' \
  -d ~/.local/share/godot/export_templates/4.7.2.stable
```

## Build

```bash
tools/run-tests.sh          # everything green first
tools/export-linux.sh       # builds build/linux/ and smoke-tests the exported binary
```

`build/linux/` then contains:
- `CrossroadsInn.x86_64`, the game;
- `CrossroadsInn.pck`, the game data: scripts, art, and `params.json` and `bram_llm.json`;
- `THIRD_PARTY_NOTICES.txt`, with the Godot licence, every component's copyright lines and licence, the full licence texts, and the AI model notices.

Tests, test fixtures, GUT and the eval tools are left out of the build.

The smoke test runs `CrossroadsInn.x86_64 --headless -- --smoke-test`. The exported game plays a full week by itself. It must report that the params loaded, all 7 images loaded, and the week ended.

## Bram's LLM on players' machines

The build doesn't include any AI model and never contacts an online service. "Bram's lines written by local AI" is an in-game checkbox, off by default and saved in `user://settings.cfg`. If a player turns it on and runs Ollama locally with `ollama pull qwen3:4b-instruct`, Bram's lines are phrased by that model and marked "(local AI)". Otherwise he uses his hand-written lines, with no error. To remove the feature from a build entirely, set `"enabled": false` in `game/data/bram_llm.json` before exporting.

The export script also checks that `THIRD_PARTY_NOTICES.txt` contains the licence texts, and that the exported game found its LLM settings file (`"llm_config":"ok"`), so a build can't silently ship without them.

## Steam

See `docs/steam-ai-disclosure.md` for the drafted AI-content answers. Uploading needs a Steamworks account and SteamCMD, which this project doesn't set up.
