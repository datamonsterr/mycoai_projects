---
inclusion: fileMatch
fileMatchPattern: "**/graduation_report/**"
---

# LaTeX Academic Report Writing

## Toolchain

- **Compiler**: pdflatex (TinyTeX) — no XeLaTeX/LuaLaTeX, no Docker
- **Build**: `latexmk -pdf -interaction=nonstopmode main.tex` or `./render.sh`
- **Bib**: bibtex (style=ieee)
- **Figures**: PNG/JPG at 150-300 DPI, `\graphicspath{{figures/}}`
- **Font**: Times (`\usepackage{times}`)

## Mandatory Pre-Read

Before editing thesis content, read in this order:
1. `docs/graduation_report/README.md`
2. `docs/graduation_report/reviews/`
3. `docs/graduation_report/plans/`
4. `docs/graduation_report/rules/`

## Key Conventions

- Use `\subfile{Chapter/X}` — NOT `\include` or `\input`
- Labels must be unique across all subfiles (they merge globally)
- NO raw Unicode outside math mode (use `$\rightarrow$`, `---`, `--`)
- Vietnamese characters OK (T5 encoding)
- Define acronyms in `glossary.tex` with `\newacronym`
- Use `booktabs` for tables (no vertical rules)
- Prefer math expressions over code listings in main body

## Content Rules

1. **Prefer math/plain English over code** — code belongs in appendices
2. **Dive deep** — inventory ALL completed experiments before writing
3. **Visual evidence** — every experiment needs data table + chart + image
4. **Define symbols at point of use** — reader with no codebase access must understand
5. **Every figure supports a finding** — lead-in, reference, and analysis required

## Build Commands

```bash
./render.sh                    # full render
./render.sh --clean            # clean
./render.sh --deps             # install missing TinyTeX packages
./render.sh --watch            # live preview
```

## Do NOT

- Use XeLaTeX/LuaLaTeX
- Use `\include` — use `\subfile`
- Duplicate labels across subfiles
- Use raw Unicode arrows/em-dashes/box-drawing
- Put `\mathcal` outside math mode
- Add Docker for LaTeX compilation
