# Crossroads Inn - Design Doc (v0.2)

## Pitch
You run a tiny inn at a crossroads for 7 in-game days. Each day, 3-5 travelers arrive wanting a room, a meal, or both. Wanderers pay in news instead of coins. Balance coins, food, and firewood, decide who to serve, and survive a final-night event.

## Scope limits
- Single screen, mouse-driven. No character movement, physics, or animation beyond simple tweens.
- Six traveler types, a handful of random events.
- One recurring NPC, Bram, who chats with the player.
- Target: roughly 100-300 lines of core game logic.

## Core loop (per day)
1. Morning: pay daily upkeep, see stock (coins, food, firewood), weather and any news, and buy food or firewood at the village market.
2. Travelers arrive one at a time with a need (room, meal, or both).
3. Player accepts, declines, or haggles. Serving costs resources and pays coins.
4. Night: firewood is consumed; shortages have consequences.
5. Day summary, then next day.

## Resources
- Coins: score and buying power.
- Food: consumed by meals.
- Firewood: consumed each night. Each occupied room needs a lit hearth, and cold or snowy nights burn more.
- Goodwill (hidden): rises when you feed pilgrims, and falls when a noble walks out or you run short of firewood. It raises pay, brings an extra traveler, and stops the final-night robbery.

## Traveler types
- Merchant: room + meal, pays well. Sometimes a **thief** in disguise who steals some of your coins at night. Bram may hint at it, but the hint is not always right.
- Pilgrim: meal, pays almost nothing, raises goodwill.
- Soldier: room, pays well, but the room needs firewood (the cold-night dilemma).
- Noble: room, opens low. You can haggle: push too far and he walks out, costing goodwill and one traveler tomorrow.
- Wanderer: meal, pays in news (tomorrow's weather, the next cheap firewood day, or the final-night event).

## Weather, market, final night
- Weather each day: normal, cold, or snow. It changes how much firewood a night burns.
- The village market sells food and firewood. Prices vary daily, and some days have cheap firewood.
- Night 7 brings one final event: a blizzard (double firewood), hungry soldiers (lots of food), or a robbery (lose coins unless goodwill is high).

## Win / lose
- Win: the morning after day 7, pay the landlord's debt (the coin target, currently 64).
- Lose only by failing to pay: the daily upkeep (currently 3) or the final debt. Bad events and shortages cost coins or goodwill. A final-night event that "goes badly" is one that leaves you unable to pay.

## Bram (runtime AI)
- Game code produces a facts object holding only what the player could know (`game/scripts/bram/bram_facts.gd`). The code also decides what Bram talks about: the situation, such as "warn about this merchant".
- A local 4B model (Qwen3-4B Instruct, Apache 2.0, run by Ollama) phrases that as one short line. Bram's fixed lines are given as examples of his voice.
- The fixed line shows at once. The LLM line replaces it only if it arrives for the same moment and passes the checks. If Ollama isn't running, Bram simply keeps his fixed lines.
- There are two safety layers:
  - **Before the model:** facts must match a strict schema (known keys, types and words), so outside text can't reach the model.
  - **After the model:** replies are rejected if they are too long, invent numbers, break character, claim certainty about a thief, or mention things not in the facts.
- The model never changes game state. Prompt injection is tested by `game/tools/bram_eval.gd`, and the results are in `docs/bram-eval.md`. Today no fact can carry outside text, so the schema refuses every injection. The eval also measures the model on its own, which is weaker, so that any future free text (names, player input) must stay behind the schema.
- On first use, the game asks Ollama to load the model (a warm-up). Requests wait up to 60 s until the model has answered once, because giving up earlier makes Ollama abandon the load.

## Build stages
1. Paper prototype: LibreOffice spreadsheet plus a Python simulation, in `prototype/` (see `prototype/tuning-log.md`). Done.
2. Grey-box Godot prototype with text labels. Done (see below).
3. Generated 2D art (portraits, backdrop) via ComfyUI. Done: a painted inn backdrop and portraits of the five traveler types and Bram, made with SDXL base 1.0 on a local ComfyUI. See `tools/comfyui/` and `game/art/provenance.json`.
4. Optional: one 3D prop via image-to-3D, cleaned in Blender, rendered to a sprite.
5. Local-LLM dialogue for Bram. Done (see Bram above).
6. Linux export and Steam AI-disclosure review.

## Grey-box (stage 2)
- One screen in the counter layout. The traveler comes in from the door with a speech bubble, Bram stands beside the counter with his own, and the stock sits in a top bar with "N more travelers today".
- Each day runs morning market, then travelers one at a time (Accept, Decline, and Haggle for nobles), then a night summary. After day 7 comes the end screen and "Play again".
- The rules are a GDScript port of the Python simulation. They reproduce its ledgers exactly on exported test runs. The numbers come from `game/data/params.json`, exported from `balance.ods`.
- Bram picks fixed lines from a facts object that holds only what the player could know. Stage 5 swaps in a local LLM that reads the same facts.

## Balance (first pass, 2026-10-23)
All numbers live on the `Params` sheet of `prototype/balance.ods`, which is the source of truth. The key ones: start with 60 coins, 10 food and 8 firewood; 2 rooms; upkeep 3; debt 64.
The simulation's careful player wins about 77% of runs with a median of 73 coins (+14% over the debt), and the random player wins 0%. That meets the "tight" bar.
Known gap: raising the debt by 10% drops the careful player's win rate to about 59%, just under the 60% robustness floor.

## Open questions
- Whether to accept the debt-sensitivity gap or relax the bar (see `prototype/tuning-log.md`).
- Whether a week that nets only about +4 coins feels good in hand play.
- Art style.
