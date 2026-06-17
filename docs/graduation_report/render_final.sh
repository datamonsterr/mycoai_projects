#!/bin/bash
# Legacy wrapper — delegates to the lightweight render.sh (no Docker)
exec "$(dirname "$0")/render.sh" --output "$(dirname "$0")/../graduation_report.pdf" "$@"
