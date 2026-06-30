#!/usr/bin/env bash
set -euo pipefail

LATEX_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "Rendering graduation report..."

pdflatex -interaction=nonstopmode -output-directory="$LATEX_DIR" "$LATEX_DIR/main.tex"
bibtex "$LATEX_DIR/main"
pdflatex -interaction=nonstopmode -output-directory="$LATEX_DIR" "$LATEX_DIR/main.tex"
pdflatex -interaction=nonstopmode -output-directory="$LATEX_DIR" "$LATEX_DIR/main.tex"

if [ -f "$LATEX_DIR/main.pdf" ]; then
    echo "PDF rendered: $LATEX_DIR/main.pdf"
else
    echo "ERROR: PDF not generated. Check $LATEX_DIR/main.log"
    exit 1
fi
