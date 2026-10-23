# Crossroads Inn

A small top-down 2D resource-management game, built as a learning project to study the full AI-assisted game development workflow (concept -> prototype -> assets -> runtime AI -> ship).

## Tech
- Engine: Godot 4.x (GDScript). Use typed variables. Never use Godot 3 syntax or APIs (e.g. no `onready` without `@`, use `@onready`, `@export`, `signal.connect()`).
- Platform: Ubuntu Linux. Run headless where possible.
- Tests: GUT (vendored in `game/addons/gut`) for game rules; run headless with `tools/run-tests.sh`. Tests live in `game/tests/unit/`, rules in `game/scripts/rules/`.
- Keep game rules in plain scripts separate from UI so they can be tested without the editor.

## Working rules
- Read `docs/design.md` before making gameplay changes; it is the source of truth. If a decision changes, update the doc in the same commit.
- Commit small and often.
- Game state lives in code. The runtime LLM (Bram) only phrases text from facts the code supplies; it never decides outcomes.
- Keep a short log of AI successes/failures in `docs/ai-log.md` (what the agent did, what was fixed by hand, rough time spent).

## Layout (planned)
- `docs/` design doc and AI log
- `game/` Godot project
- `tools/` helper scripts (Blender headless export, ComfyUI API wrapper)
