#!/bin/bash
# Render LaTeX to PDF using Docker TeX Live

# Configuration
LATEX_DIR="/home/dat/dev/mycoai_projects/docs/graduation_report/latex"
OUTPUT_DIR="/home/dat/dev/mycoai_projects"
DOCKER_IMAGE="texlive/texlive"

echo "Rendering LaTeX to PDF..."

docker run --rm -v "$LATEX_DIR":/workdir -w /workdir "$DOCKER_IMAGE" \
    bash -c "pdflatex -interaction=nonstopmode main.tex && bibtex main && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex"

# Copy output to root
cp "$LATEX_DIR/main.pdf" "$OUTPUT_DIR/graduation_report.pdf"

echo "PDF generated: $OUTPUT_DIR/graduation_report.pdf"
