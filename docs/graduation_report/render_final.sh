#!/bin/bash
LATEX_DIR="/home/dat/dev/mycoai_projects/docs/graduation_report/latex"
docker run --rm -v "$LATEX_DIR":/workdir -w /workdir texlive/texlive:latest bash -c "pdflatex -interaction=nonstopmode main.tex && bibtex main && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex"
