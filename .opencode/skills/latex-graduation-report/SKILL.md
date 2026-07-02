---
name: latex-graduation-report
description: >
  Build, style, and render the MycoAI graduation thesis (graduation_report/main.tex).
  TRIGGERS: graduation report, graduation thesis, main.tex, render latex, compile thesis,
  build pdf, latex styling, academic report style, chapter formatting.
allowed-tools: Read, Edit, Bash
---

# Graduation Report LaTeX Workflow

## Quick Build

```bash
cd graduation_report && latexmk -pdf -interaction=nonstopmode main.tex
```

Produces `graduation_report/main.pdf`. No Docker needed — uses TinyTeX.

## Toolchain

- **Compiler**: `pdflatex` (TinyTeX) — lightweight, no Docker
- **Build**: `latexmk -pdf -interaction=nonstopmode main.tex` from `graduation_report/`
- **Bib**: `bibtex` + `biblatex` (style=ieee)
- **Figures**: PNG @ 150-300 DPI in `graduation_report/figures/`
- **Deps**: install missing TeX packages with `tlmgr` as needed

## Document Structure

```
graduation_report/
├── main.tex              # Preamble + chapter includes
├── Cover.tex             # Title page
├── glossary.tex          # Acronym definitions
├── lstlisting.tex        # Code listing style
├── reference.bib         # Bibliography
├── figures/              # PNG/JPG images
└── Chapter/              # Subfiles per chapter
    ├── 0_2_Acknowledgment.tex
    ├── 0_3_Abstract.tex
    ├── Introduction.tex
    ├── Retrieval_Model_Research.tex
    ├── Web_Application.tex
    ├── Agentic_Engineering.tex
    ├── Conclusion.tex
    └── Appendix_B.tex
```

## Common Commands

```bash
cd graduation_report && latexmk -pdf -interaction=nonstopmode main.tex
cd graduation_report && latexmk -c
cd graduation_report && latexmk -pvc -pdf -interaction=nonstopmode main.tex
```

## Writing Rules

Follow `.opencode/rules/latex-academic-reports.md` for:

- Chapter structure (`\subfile{}` not `\include{}`)
- Figure/table/listings conventions
- Label naming (`fig:`, `tab:`, `sec:`, `eq:` prefixes)
- Math mode rules (no `\mathcal` outside `$...$`)
- Unicode replacements (`→` → `$\rightarrow$`, `—` → `---`)
- Format selection by content type
- Acronym management in `glossary.tex`

## Content Format Quick Pick

| Content | LaTeX Format | Example |
|---|---|---|
| Code block | `lstlisting` | `\begin{lstlisting}[language=Python]` |
| Inline code | `\texttt{}` | `\texttt{GET /api/v1/images}` |
| Terminal output | `verbatim` | `\begin{verbatim}` |
| Equation | `\[...\]` or `equation` | `\[ f(x) = x^2 \]` |
| Diagram | `\includegraphics` PNG | 200+ DPI Mermaid export |
| Screenshot | `\includegraphics` PNG | 150 DPI, cropped |
| Table | `booktabs` tabular | `\toprule`, `\midrule`, `\bottomrule` |
| List | `itemize` / `enumerate` | `\begin{itemize}` |
| Callout | `quote` | `\begin{quote}` |

## Troubleshooting

| Problem | Fix |
|---|---|
| Missing .sty file | `./render.sh --deps` |
| `\mathcal` outside math | Wrap in `$...$` |
| Unicode char error | Replace with LaTeX equivalent |
| Duplicate labels | Rename globally unique |
| Undefined citation | Add entry to `reference.bib` |
| Extra alignment tab | Match `&` count to `tabular` preamble |
