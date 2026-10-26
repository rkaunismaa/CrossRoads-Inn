#!/usr/bin/env bash
# Export the Linux build to build/linux/ and smoke-test it: the exported binary plays a full
# week headless and must report that params and all art loaded. Needs Godot's 4.7.2 export
# templates in ~/.local/share/godot/export_templates/4.7.2.stable/ (see docs/release.md).
set -euo pipefail

GODOT="${GODOT:-godot}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/build/linux"
BIN="$OUT/CrossroadsInn.x86_64"

rm -rf "$OUT"
mkdir -p "$OUT"
"$GODOT" --headless --path "$ROOT/game" --import >/dev/null 2>&1 || true
"$GODOT" --headless --path "$ROOT/game" --export-release "Linux" "$BIN"
"$GODOT" --headless --path "$ROOT/game" --script res://tools/write_notices.gd -- "$OUT/THIRD_PARTY_NOTICES.txt"

echo "--- smoke test of the exported build ---"
smoke="$(CROSSROADS_LLM=off "$BIN" --headless -- --smoke-test 2>&1 | grep '^SMOKE ' || true)"
echo "$smoke"
if [[ "$smoke" != *'"ok":true'* || "$smoke" != *'"art_loaded":7'* || "$smoke" != *'"params":"ok"'* ]]; then
	echo "export-linux: smoke test FAILED" >&2
	exit 1
fi
echo "export-linux: OK -> $OUT"
ls -la "$OUT"
