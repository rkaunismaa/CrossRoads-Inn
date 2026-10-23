# Crossroads Inn

You run a tiny inn at a crossroads for 7 days. Each day, 3-5 travelers arrive wanting a room, a meal, or both. Merchants (some of them thieves), pilgrims, soldiers, haggling nobles and news-bearing wanderers all come through.

You balance coins, food and firewood against the weather, pay the daily upkeep, and survive a final-night event. Then you pay the landlord's debt.

This is a learning project. It studies the full AI-assisted game development workflow: concept, prototype, assets, runtime AI, and shipping. Every step is recorded in [`docs/session-history.md`](docs/session-history.md).

## Status

- **Stage 1, the paper prototype, is done.** The balance numbers are tuned. See [`prototype/tuning-log.md`](prototype/tuning-log.md).
- **Stage 2, the grey-box Godot prototype, is done.** You can play a full week. Its rules match the simulation exactly, and Bram speaks fixed lines.
- **Stage 3, generated 2D art, is done.** A painted backdrop and portraits, made locally with SDXL in ComfyUI. Every image is reproducible from `tools/comfyui/assets.json`.
- **Stage 5, Bram's local-LLM dialogue, is done.** A local Qwen3-4B phrases his lines from game facts, behind two safety layers. See [`docs/bram-eval.md`](docs/bram-eval.md).
- **Stage 4, an optional 3D prop, or stage 6, Linux export and the Steam AI-disclosure review, is next.**

## Layout

| Path | What's there |
|---|---|
| `docs/design.md` | The design doc. It is the source of truth for gameplay. |
| `docs/session-history.md` | A step-by-step record of every AI-assisted session. |
| `docs/ai-log.md` | Short notes on what the AI did well or badly, and the time spent. |
| `docs/superpowers/` | Specs and implementation plans. |
| `prototype/` | The paper prototype: a Python simulation (`inn_sim`) and the `balance.ods` workbook. |
| `game/` | The Godot 4 project, with GUT tests. |
| `tools/` | Helper scripts: `run-tests.sh`, and `comfyui/` for generating the art. |
| `game/art/` | Generated art plus `provenance.json` (the prompt, seed and model behind each image). |

## Requirements

- Ubuntu Linux (other platforms are untested).
- [Godot 4.7](https://godotengine.org/), run as `godot` on your `PATH`.
- Python 3.10 or newer with `pytest`.
- Optional: [Ollama](https://ollama.com/) with `ollama pull qwen3:4b-instruct`, for Bram's LLM dialogue. Without it, Bram uses his fixed lines.
- LibreOffice 7.3 or newer with the Python bridge (`python3-uno`). The simulation reads the workbook without it, but writing to the workbook and the hand-play commands need it.

## Godot game

```bash
tools/run-tests.sh                 # GUT tests, headless (fails on any script error)
godot --path game                  # play the grey-box game
```

**How to play.**
1. Each morning, buy food and firewood, then press **Open the doors**.
2. Travelers come to the counter one at a time. **Accept** or **Decline** them. Nobles can also be haggled with. A greyed-out button shows why when you hover over it.
3. After the night summary, press **Continue**.
4. After day 7, you either pay the landlord or you don't.

**Bram's LLM.** Settings are in `game/data/bram_llm.json`; set `"enabled": false` to turn it off. Evaluate it against the real model (Ollama running) with:

```bash
godot --headless --path game --script res://tools/bram_eval.gd   # writes docs/bram-eval.md
CROSSROADS_LLM_LIVE=1 tools/run-tests.sh                        # includes the one live-model test
```

**After re-tuning `balance.ods`**, regenerate what the game uses:

```bash
cd prototype
python3 -m inn_sim export            # game/data/params.json
python3 -m inn_sim export-fixtures   # game/tests/fixtures/ (Python ledgers the GDScript rules must match)
```

The Python tests fail if either is out of date.

## Paper prototype

All tunable numbers live on the `Params` sheet of `prototype/balance.ods`. The game rules live only in Python. Run everything from `prototype/`:

```bash
cd prototype
python3 -m pytest -q                              # tests
python3 -m inn_sim simulate --runs 5000           # careful vs random player, judged against the balance bar
python3 -m inn_sim sensitivity                    # nudge each number by ±10% and flag fragile ones
```

### Play it by hand, one day at a time

```bash
python3 -m inn_sim deal --seed 5 --daily   # deals day 1 into the HandPlay sheet
```

1. Open `balance.ods` in LibreOffice Calc.
2. Fill in `buy_food` and `buy_firewood` on the day's first row, and a `decision` for each traveler: `accept`, `decline`, `haggle_mid` or `haggle_high` (the last two are nobles only).
3. Save and close Calc.
4. Run `python3 -m inn_sim next`. It shows how the day went and then deals the next day.

After day 7 you see your result next to the careful player's on the same run, and the `Reveal` sheet shows what was hidden.

To deal the whole week at once instead, use `deal --seed 5`, fill in every day, then run `python3 -m inn_sim replay`.

## How AI is used

- The game was designed and built with Claude Code. See the session history.
- All art is AI-generated with Stable Diffusion XL base 1.0 (CreativeML Open RAIL++-M license) on a local ComfyUI. Prompts and seeds are recorded in `game/art/provenance.json`.
- At runtime, a small local LLM (Qwen3-4B Instruct via Ollama, Apache 2.0) voices Bram, the recurring NPC who chats with the player. It only phrases facts the game code supplies, and it never decides outcomes.
