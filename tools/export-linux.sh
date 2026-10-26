#!/usr/bin/env bash
# Export the Linux build to build/linux/ and check it: the exported binary plays a full week
# headless and must report that params, all art and the LLM settings loaded; the notices must
# contain the licence texts. Needs Godot's 4.7.2 export templates (see docs/release.md).
set -euo pipefail

GODOT="${GODOT:-godot}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/build/linux"
BIN="$OUT/CrossroadsInn.x86_64"
fail() { echo "export-linux: $*" >&2; exit 1; }

rm -rf "$OUT"
mkdir -p "$OUT"
"$GODOT" --headless --path "$ROOT/game" --import >/dev/null 2>&1 || true
"$GODOT" --headless --path "$ROOT/game" --export-release "Linux" "$BIN"
timeout 120 "$GODOT" --headless --path "$ROOT/game" --script res://tools/write_notices.gd -- "$OUT/THIRD_PARTY_NOTICES.txt" \
	|| fail "writing THIRD_PARTY_NOTICES.txt failed"
grep -q "Apache License" "$OUT/THIRD_PARTY_NOTICES.txt" && grep -q "FreeType" "$OUT/THIRD_PARTY_NOTICES.txt" \
	|| fail "THIRD_PARTY_NOTICES.txt is missing licence texts"

echo "--- smoke test of the exported build ---"
set +e
log="$(CROSSROADS_LLM=off timeout 120 "$BIN" --headless -- --smoke-test 2>&1)"
status=$?
set -e
smoke="$(grep '^SMOKE ' <<<"$log" || true)"
echo "$smoke"
[[ $status -eq 124 ]] && fail "smoke test timed out"
[[ $status -ne 0 ]] && { echo "$log" | tail -20 >&2; fail "exported game exited with status $status"; }
for want in '"ok":true' '"art_loaded":7' '"params":"ok"' '"llm_config":"ok"'; do
	[[ "$smoke" == *"$want"* ]] || fail "smoke test FAILED: expected $want"
done
echo "export-linux: OK -> $OUT"
ls -la "$OUT"
