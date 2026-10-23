#!/usr/bin/env bash
# Run the GUT test suite headless. Usage: tools/run-tests.sh [extra gut_cli args]
# Fails if any test fails OR if Godot reports a script error: GUT silently skips
# test scripts that don't parse, which would otherwise look like a pass.
set -uo pipefail

GODOT="${GODOT:-godot}"
GAME_DIR="$(cd "$(dirname "$0")/../game" && pwd)"

# Import once so class_name scripts are registered in a fresh checkout.
"$GODOT" --headless --path "$GAME_DIR" --import >/dev/null 2>&1 || true

out="$(mktemp)"
trap 'rm -f "$out"' EXIT
"$GODOT" --headless --path "$GAME_DIR" -s res://addons/gut/gut_cmdln.gd "$@" 2>&1 | tee "$out"
status=${PIPESTATUS[0]}

if grep -q "SCRIPT ERROR" "$out"; then
	echo "run-tests: Godot reported script errors (see above); failing the run." >&2
	exit 1
fi
exit "$status"
