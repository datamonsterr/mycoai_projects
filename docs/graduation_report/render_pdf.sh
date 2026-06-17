#!/bin/bash
# Legacy wrapper — delegates to the lightweight render.sh (no Docker)
exec "$(dirname "$0")/render.sh" "$@"
