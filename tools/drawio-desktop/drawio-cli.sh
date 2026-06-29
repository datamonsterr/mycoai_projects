#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APPIMAGE="$ROOT/drawio.AppImage"
exec "$APPIMAGE" --appimage-extract-and-run --no-sandbox "$@"
