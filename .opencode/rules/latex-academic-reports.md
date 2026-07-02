# Rule: LaTeX Academic Report Writing

## Scope

Applies to all LaTeX academic documents in `docs/`, `report/`, and any
`main.tex` using TinyTeX (pdflatex).

## Toolchain

- **Compiler**: pdflatex (TinyTeX) — no XeLaTeX/LuaLaTeX, no Docker
- **Build**: `latexmk -pdf -interaction=nonstopmode main.tex` from `graduation_report/` or a repo-local build wrapper that runs there
- **Bib**: bibtex (backend=bibtex, style=ieee)
- **Figures**: PNG/JPG at 150–300 DPI, `\graphicspath{{figures/}}`
- **Font**: Times (`\usepackage{times}`) — compact, academic, works with T5 encoding

## Document Structure

```
report/latex/
├── main.tex              # Preamble + \subfile{Chapter/X} + \printbibliography
├── Cover.tex             # \begin{titlepage} ... \end{titlepage}
├── glossary.tex          # \newacronym{key}{ABBR}{Definition}
├── lstlisting.tex        # \lstset{...} code style config
├── reference.bib         # BibTeX entries
├── figures/              # PNG/JPG images
├── Chapter/              # \subfile targets
│   ├── 0_2_Acknowledgment.tex
│   ├── 0_3_Abstract.tex
│   ├── 1_Introduction.tex
│   ├── ...
│   └── Appendix_B.tex
└── chapter/              # Alternative chapter drafts (lower priority)
```

## Writing Conventions

### Chapters
- Use `\subfile{Chapter/X_Name}` — NOT `\include` or `\input`
- Chapter titles via `\chapter{TITLE}` in main.tex preamble
- Subfile starts directly with `\section{...}` or `\subsection{...}`

### Labels
- `\label{fig:name}` for figures
- `\label{tab:name}` for tables
- `\label{sec:name}` for sections
- `\label{eq:name}` for equations
- Labels MUST be unique across all subfiles (they merge into one document)

### Figures
```latex
\begin{figure}[h]
\centering
\includegraphics[width=\textwidth,keepaspectratio]{figures/name.png}
\caption{Caption text}\label{fig:name}
\end{figure}
```
- PNG preferred over JPG for diagrams/charts
- Screenshots at 150 DPI, diagrams at 200+ DPI
- Always include `\label` inside or after `\caption`

### Tables
```latex
\begin{table}[h]
\centering
\caption{Table caption}\label{tab:name}
\begin{tabular}{@{}lcr@{}}
\toprule
Header1 & Header2 & Header3 \\
\midrule
...
\bottomrule
\end{tabular}
\end{table}
```
- Use `booktabs` (`\toprule`, `\midrule`, `\bottomrule`)
- No vertical rules
- `@{}` removes column padding at edges

### Code Listings
```latex
\begin{lstlisting}[language=Python, caption={Description}, label={lst:name}]
code here
\end{lstlisting}
```
- Configured in `lstlisting.tex`
- Use `\texttt{inline}` for short code references in text

### Math
- Display: `\[ ... \]` or `\begin{equation} ... \end{equation}`
- Inline: `$...$`
- `\mathcal`, `\mathbf`, `\text` only inside math mode
- Never use `\_` outside math mode — use `\textunderscore` or `\_` in `\texttt`

### Referencing
- Figures: `Figure~\ref{fig:name}`
- Tables: `Table~\ref{tab:name}`
- Sections: `Section~\ref{sec:name}`
- Citations: `\cite{key}`, `\parencite{key}`

### Unicode
- NO raw Unicode outside math mode (box-drawing, arrows, em-dashes)
- Replace `→` with `$\rightarrow$`
- Replace `—` with `---`
- Replace `–` with `--`
- Replace box-drawing chars (`├`, `└`, `│`) with ASCII (`+--`, `\--`, `|`)
- Vietnamese characters OK (T5 encoding handles them)

### Acronyms
- Define in `glossary.tex` with `\newacronym{key}{ABBR}{Full Name}`
- Never define acronyms inline in chapters
- First use: `\gls{key}` (shows full + abbrev)
- Subsequent: `\gls{key}` (shows abbrev only)

## Content Format Selection

| Content Type | Best Format | Notes |
|---|---|---|
| Code blocks | `lstlisting` | Syntax-highlighted, numbered lines |
| Inline code | `\texttt{}` | Monospace, no breaks |
| Terminal output | `\begin{verbatim}` | Preserves whitespace/ASCII art |
| Equations | `\[...\]` or `\begin{equation}` | Numbered if referenced |
| Diagrams | PNG via `\includegraphics` | Export from Mermaid/PlantUML at 200+ DPI |
| Screenshots | PNG `\includegraphics` | 150 DPI, crop to relevant area |
| Architecture diagrams | PNG/PDF `\includegraphics` | Vector preferred, PNG at 300 DPI fallback |
| Tables | `booktabs` tabular | No vertical lines, 3 horizontal rules |
| Bullet lists | `itemize` or `enumerate` | Use `enumitem` for spacing control |
| Quotes/callouts | `\begin{quote}` | For important notes, placeholders |

## Build Command

```bash
# Full render
./render.sh

# Specific directory
./render.sh /path/to/latex/folder

# Clean artifacts
./render.sh --clean

# Install missing deps
./render.sh --deps

# Live preview
./render.sh --watch

# Output to specific path
./render.sh --output ../report.pdf
```

## Package Policy

- **Default**: TinyTeX (~300 MB) — covers 95% of academic writing
- **Add packages only when needed**: `tlmgr install <pkg>` or `./render.sh --deps`
- **NO full TeX Live** (~7 GB) — massive overkill
- **NO Docker** for compilation — adds 500MB+ overhead, TinyTeX handles it

## Do NOT

- Do NOT use XeLaTeX/LuaLaTeX — pdflatex is sufficient
- Do NOT use `\include` — use `\subfile` for chapter files
- Do NOT duplicate labels across subfiles — they merge globally
- Do NOT use raw Unicode arrows/em-dashes/box-drawing — use LaTeX equivalents
- Do NOT put `\mathcal` or math commands outside math mode
- Do NOT add Docker as a dependency for LaTeX compilation
