---
name: latex-graduation-report
description: >
  Build, style, and render the MycoAI graduation thesis (docs/graduation_report/latex/main.tex).
  TRIGGERS: graduation report, graduation thesis, main.tex, render latex, compile thesis,
  build pdf, latex styling, academic report style, chapter formatting.
allowed-tools: Read, Edit, Bash
---

# Graduation Report LaTeX Workflow

## Quick Build

```bash
cd docs/graduation_report && ./render.sh
```

Produces `latex/main.pdf` (~3.5MB, ~70 pages). No Docker needed — uses TinyTeX.

## Toolchain

- **Compiler**: `pdflatex` (TinyTeX) — lightweight, no Docker
- **Build**: `./render.sh` (wraps latexmk with pdflatex → bibtex → pdflatex×N)
- **Bib**: `bibtex` + `biblatex` (style=ieee)
- **Figures**: PNG @ 150-300 DPI in `latex/figures/`
- **Deps**: `./render.sh --deps` auto-installs missing packages

## Document Structure

```
docs/graduation_report/
├── render.sh             # Build script (clean/render/watch/deps modes)
├── latex/
│   ├── main.tex          # Preamble + chapter includes
│   ├── Cover.tex         # Title page
│   ├── glossary.tex      # Acronym definitions
│   ├── lstlisting.tex    # Code listing style
│   ├── reference.bib     # Bibliography
│   ├── figures/          # PNG/JPG images
│   └── Chapter/          # Subfiles per chapter
│       ├── 0_2_Acknowledgment.tex
│       ├── 0_3_Abstract.tex
│       ├── 1_Introduction.tex
│       ├── 2_Literature_Review.tex
│       ├── 3_Methodology.tex
│       ├── 4_Implementation.tex
│       ├── 5_Evaluation.tex
│       └── Appendix_B.tex
└── render_pdf.sh         # Legacy wrapper → delegates to render.sh
```

## Common Commands

```bash
./render.sh                  # Full compile (clean + pdflatex + bibtex + passes)
./render.sh --clean          # Remove build artifacts only
./render.sh --watch          # Live preview (auto-rebuild on save)
./render.sh --deps           # Install missing TeX packages
./render.sh --output /tmp/x  # Build + copy PDF to specified path
./render.sh --force          # Continue past warnings
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
