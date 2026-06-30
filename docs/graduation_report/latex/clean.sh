#!/usr/bin/env bash
set -euo pipefail

LATEX_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Cleaning LaTeX render artifacts in $LATEX_DIR..."

rm -f "$LATEX_DIR"/main.aux
rm -f "$LATEX_DIR"/main.bbl
rm -f "$LATEX_DIR"/main.blg
rm -f "$LATEX_DIR"/main-blx.bib
rm -f "$LATEX_DIR"/main.fdb_latexmk
rm -f "$LATEX_DIR"/main.fls
rm -f "$LATEX_DIR"/main.lof
rm -f "$LATEX_DIR"/main.log
rm -f "$LATEX_DIR"/main.lot
rm -f "$LATEX_DIR"/main.out
rm -f "$LATEX_DIR"/main.pdf
rm -f "$LATEX_DIR"/main.run.xml
rm -f "$LATEX_DIR"/main.toc
rm -f "$LATEX_DIR"/main.synctex.gz

echo "Done. Only .tex, figures/, tables/, contents, and *.zip remain."
