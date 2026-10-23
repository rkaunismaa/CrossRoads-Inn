# Crossroads Inn - Design Doc (v0.1)

## Pitch
You run a tiny inn at a crossroads for 7 in-game days. Each day, 3-5 travelers arrive wanting a room, a meal, or news. Balance coins, food, and firewood, decide who to serve, and survive a final-night event.

## Scope limits
- Single screen, mouse-driven. No character movement, physics, or animation beyond simple tweens.
- Six traveler types, a handful of random events.
- One recurring NPC, Bram, who chats with the player.
- Target: roughly 100-300 lines of core game logic.

## Core loop (per day)
1. Morning: see stock (coins, food, firewood) and the day's events.
2. Travelers arrive one at a time with a need (room, meal, news).
3. Player accepts, declines, or haggles. Serving costs resources and pays coins.
4. Night: firewood is consumed; shortages have consequences.
5. Day summary, then next day.

## Resources
- Coins: score and buying power.
- Food: consumed by meals.
- Firewood: consumed each night (more in cold weather).

## Traveler types (draft, to balance on paper first)
Merchant, Pilgrim, Soldier, Thief, Noble, Wanderer. Each has a need, a payment range, and a risk.

## Win / lose
- Survive 7 days with coins >= a target (TBD after paper playtest).
- Lose if the inn cannot pay its debts or a final-night event goes badly.

## Bram (runtime AI, later stage)
- Game code produces a facts object (e.g. food low, stranger hostile, day number).
- A local 3-4B model turns facts into one or two lines of dialogue.
- The model never changes game state. Test with prompt injection.

## Build stages
1. Paper prototype (index cards or spreadsheet) to balance numbers.
2. Grey-box Godot prototype with text labels.
3. Generated 2D art (portraits, backdrop) via ComfyUI.
4. Optional: one 3D prop via image-to-3D, cleaned in Blender, rendered to a sprite.
5. Local-LLM dialogue for Bram.
6. Linux export and Steam AI-disclosure review.

## Open questions
- Exact balance numbers.
- Win condition target.
- Art style.
