#!/usr/bin/env bash
# Run the GUT test suite headless. Usage: tools/run-tests.sh [extra gut_cli args]
set -euo pipefail

GODOT="${GODOT:-godot}"
GAME_DIR="$(cd "$(dirname "$0")/../game" && pwd)"

# Import once so class_name scripts are registered in a fresh checkout.
"$GODOT" --headless --path "$GAME_DIR" --import >/dev/null 2>&1 || true

exec "$GODOT" --headless --path "$GAME_DIR" -s res://addons/gut/gut_cmdln.gd "$@"
