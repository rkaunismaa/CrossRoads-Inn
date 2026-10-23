# AI Log

Short notes on what the agent did, what was fixed by hand, and rough time spent.

## 2026-10-23 - Godot project scaffold
- Agent: installed Godot 4.7.2 to `~/.local/bin/godot` (checksum verified), vendored GUT 9.7.1 into `game/addons/gut`, created `project.godot`, a grey-box main scene, a plain `InnState` rules class, two GUT tests, and `tools/run-tests.sh`.
- Verified: tests pass headless (exit 0), a deliberately failing test exits 1, main scene runs headless with no errors.
- Fixed by hand: nothing.
- Time: ~10 min.
