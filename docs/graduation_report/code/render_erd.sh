#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/../../.."
SRC="$ROOT/docs/graduation_report/latex/figures/src"
OUT="$ROOT/docs/graduation_report/latex/figures"
DBML="$SRC/ch03_erd.dbml"
SVG=/tmp/opencode/erd_output.svg

DBML_RENDERER="${DBML_RENDERER:-/tmp/opencode/dbml/node_modules/.bin/dbml-renderer}"
echo "Rendering ERD from DBML..."
"$DBML_RENDERER" -i "$DBML" -o "$SVG" 2>&1

echo "Converting SVG to PNG..."
rsvg-convert --width 3600 --keep-aspect-ratio "$SVG" -o "$OUT/ch03_erd.png"
echo "  -> $OUT/ch03_erd.png ($(stat -c%s "$OUT/ch03_erd.png") bytes)"
