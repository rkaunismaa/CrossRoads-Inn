# Grey-box Godot Prototype (Stage 2) - Design

Date: 2026-10-23
Status: approved by user 2026-10-23

## Intent

Stage 1 tuned Crossroads Inn's rules and numbers in a Python simulation (`prototype/inn_sim`, numbers in `prototype/balance.ods`). Stage 2 turns that into a playable Godot game with plain grey boxes and text: one full week at the inn, with the same rules and numbers the simulation balanced.

It also lays the groundwork for stage 3, where generated art replaces the grey boxes, and stage 5, where a local LLM voices Bram.

It is part of the project's study of AI-assisted game development, so the work is logged in `docs/session-history.md` and `docs/ai-log.md`.

## Goals (chosen by the user: options 1, 2 and 3)

1. **A full week you can play.** Market, travelers at the counter, night, final-night event, and a win or lose screen, all grey boxes and text. The rules are written in GDScript, kept separate from the screen code, and tested with GUT.
2. **Same results as the simulation.** For the same dealt run and the same decisions, the GDScript rules produce exactly the Python ledger.
3. **Bram speaks, with fixed lines.** The game builds a facts object, and Bram chooses a hand-written line from it. Bram never changes the game.

## Non-goals

- Art, sound, music or animation beyond simple tweens.
- Saving or loading a game.
- Choosing a seed in the game, or matching Python's random dealing. Godot deals its own runs for play.
- A Linux export or build.
- An in-game careful or random player.
- The LLM for Bram (stage 5).

## Anti-goals

- Rules that drift from the simulation, so that the balance tuned in stage 1 no longer applies.
- Game rules inside UI scripts, or rules that need the editor or a scene to test (see CLAUDE.md).
- Bram's text affecting outcomes in any way.
- Balance numbers hard-coded in GDScript.

## Constraints

- Godot 4.7, typed GDScript, Godot 4 syntax only (see CLAUDE.md). GUT 9.7.1 is already installed, and `tools/run-tests.sh` runs it headless.
- The rules live in plain scripts (`RefCounted`, not nodes) under `game/scripts/rules/`. UI lives under `game/scenes/`.
- `docs/design.md` is the source of truth for gameplay. Stage 2 does not change gameplay. If something has to change, update the design doc in the same commit.

## What gets built

### Screen layout (the counter, picked from mockups; agent's call between options)
- **Top bar:** coins, food, firewood, rooms used/total, day number and weather. *My addition:* "N more travelers today", showing the real arrival count, the same information the simulation's careful player has.
- **Main area:** a side view of the inn. On the left is the door, where the traveler's grey box enters (a simple tween is fine) with a speech bubble stating their need and offer. In the middle is the counter. On the right is Bram's grey box with his speech bubble.
- **Buttons:**
  - Accept and Decline.
  - For a noble, also "Haggle: ask 10" and "Haggle: ask 12", with the values taken from the params.
  - A button is disabled when the action is impossible (no room or no food), and its tooltip says why.

### Day flow
1. **Morning panel:**
   - Upkeep is paid automatically. If you can't pay, the run ends with a loss.
   - The panel shows weather, food and firewood prices (a cheap firewood day is marked as such), news you have collected, and how many travelers are coming.
   - Buy food and firewood with + and − controls. These can't go beyond what your coins allow, and food is bought first, as in the rules.
   - Then "Open the doors".
2. **Travelers come one at a time** to the counter. Each decision is applied and the outcome is shown briefly: "accepted +8", "declined (no room)", "noble walked out". News from a wanderer goes into a news list on the morning panel.
3. **Night summary:** shows what was burned and any shortage, any theft, and the stock after the night. These are the same facts the `next` command prints. On night 7 it also shows the final event.
4. **End screen** after night 7: win or lose, ending coins against the debt, and a short summary of the week.
5. Reaching the end, or losing early, offers "Play again", which deals a new random run.

### The rules in GDScript (`game/scripts/rules/`)
- A port of `inn_sim` covering the model, dealing, the rules and the ledger strings. It covers the day order, the needs table, goodwill (hidden, clamped), noble haggling and walk-outs, thief hints and theft, night fire with shortage penalties, the final events, and arrivals adjusted by goodwill and walk-outs.
- The existing `InnState` class grows into the full state.
- The UI calls the rules and only displays what they return. Like `play_days`, the rules can be advanced one step at a time: morning, then each traveler, then the night.
- **Dealing:** Godot deals runs with `RandomNumberGenerator` using the same probabilities and weights. Its random draws are not expected to match Python's.

### Same results as the simulation (agent's call on how)
- A new Python command, `python3 -m inn_sim export-fixtures`, writes JSON files to `game/tests/fixtures/`. Each one holds:
  - a dealt run (the full `RunDeal`);
  - the decisions (the market buys per day, plus an action for each arrived traveler);
  - the expected ledger from `play_run`;
  - the params used.
- There are at least 20 fixtures. They mix careful-player and random-player decisions so that walk-outs, thefts, shortages, losses and every final event are covered.
- A GUT test loads every fixture and plays it through the GDScript rules. It asserts the ledger matches **line for line**, which also means the ledger strings must be identical.
- *(Agent's call)* A few fixtures use scripted decisions with deliberately illegal actions, such as accepting with no room, accepting with no food, or haggling with a non-noble, so the decline branches are checked too.
- *(Agent's call)* Python's `round()` rounds halves to the even number, but GDScript's `round()` rounds them away from zero. The port copies Python's rounding wherever the rules round (goodwill-adjusted pay and the dealt prices).

### Where the numbers come from (agent's call)
- `balance.ods` stays the single source of truth.
- A new command, `python3 -m inn_sim export`, writes `game/data/params.json` from it, and the game loads that file at startup.
- A Python test fails if `params.json` doesn't match `balance.ods`, so tuning can't silently fall out of sync.

### Bram (agent's call on details)
- *(Agent's call)* The facts hold only what the player could know: the dealt hint, the stock, the weather, prices and news collected so far. Hidden values never go in: `is_thief`, the noble's tier, goodwill, and an unannounced final event. That stops Bram leaking secrets, now and when the LLM reads the same facts in stage 5.
- The rules side builds a facts dictionary at three moments: the morning, each traveler's arrival, and the night summary. Example keys:
  - `day`, `weather`, `food_low`, `firewood_short_tonight`;
  - `traveler_kind`, `suspicious` (from the dealt hint, so Bram's warning is exactly the simulation's hint);
  - `news_gained`, `final_night`.
- `game/scripts/bram/` picks a line from a hand-written table keyed by facts, with a few variants per situation. The pick is deterministic from a seed so tests are stable.
- Bram only reads facts and returns text. A test checks that asking Bram for a line leaves the game state unchanged.
- The facts object's shape is documented in the code, because stage 5 feeds it to the LLM.

## Left to the builder

- Node and scene structure, signal wiring, and the tween details.
- The exact wording of Bram's lines, as long as there are at least 2 variants for each situation he reacts to.
- How params are typed when loaded (for example a typed `InnParams` class or a dictionary), as long as nothing is hard-coded.
- Whether ledger lines are built in the rules or in a separate formatter, as long as the strings match Python exactly.

## Done when

- `tools/run-tests.sh` passes, including the parity test over every fixture.
- A full week can be played from start to end screen in the editor, and also with `godot --path game`.
- Bram comments at morning, on travelers (including a warning on suspicious merchants), and at night.
- `docs/design.md`, the README, the session history and the AI log are updated.
