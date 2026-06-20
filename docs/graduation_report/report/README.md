# MycoAI Graduation Thesis

OpenPrism-compatible LaTeX template for the MycoAI Retrieval graduation thesis.

## Structure

```
report/
├── manifest.json            # Template registry for OpenPrism
├── thesis/                  # Thesis document template
│   ├── main.tex             # Entry point — \documentclass{report}
│   ├── preamble.tex         # Packages, formatting, glossary, code style
│   ├── cover.tex            # Title page
│   ├── reference.bib        # Bibliography (BibLaTeX)
│   ├── figures/             # All figures and diagrams
│   └── sec/                 # Chapter source files
│       ├── 0_2_Acknowledgment.tex
│       ├── 0_3_Abstract.tex
│       ├── 1_Introduction.tex
│       ├── 2_Literature_Review.tex
│       ├── 3_Methodology.tex
│       ├── 4_Implementation.tex
│       ├── 5_Evaluation.tex
│       └── Appendix_B.tex
├── slides/                  # Defense presentation template
│   ├── main.tex             # Entry point — \documentclass{beamer}
│   └── preamble.tex         # Beamer theme, custom colors, footline
└── README.md
```

## Compile

### Thesis (pdflatex + bibtex)

```bash
cd thesis
pdflatex main && bibtex main && pdflatex main && pdflatex main
```

Or with latexmk:

```bash
cd thesis
latexmk -pdf main
```

### Slides (xelatex or pdflatex)

```bash
cd slides
pdflatex main
```

## OpenPrism Integration

This directory follows the [OpenPrism](https://github.com/OpenDCAI/OpenPrism) template convention:
- `manifest.json` at the template root registers both `mycoai-thesis` and `mycoai-slides`
- Templates use `main.tex` as entry point, `preamble.tex` for shared configuration
- Chapter content lives under `sec/`
- Ready for import into any OpenPrism workspace

## Content Overview

| Chapter | File | Description |
|---------|------|-------------|
| Cover | `cover.tex` | Title page with thesis info |
| Acknowledgment | `sec/0_2_Acknowledgment.tex` | Acknowledgments |
| Abstract | `sec/0_3_Abstract.tex` | Thesis abstract |
| Ch.1 | `sec/1_Introduction.tex` | Problem statement, dataset description |
| Ch.2 | `sec/2_Literature_Review.tex` | Retrieval model, segmentation, feature extraction |
| Ch.3 | `sec/3_Methodology.tex` | Web application design and implementation |
| Ch.4 | `sec/4_Implementation.tex` | Agentic engineering, evaluation |
| Ch.5 | `sec/5_Evaluation.tex` | Conclusion and future work |
| App.B | `sec/Appendix_B.tex` | Use case descriptions |
