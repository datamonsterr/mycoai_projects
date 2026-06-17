#!/usr/bin/env bash
# render.sh — Lightweight LaTeX renderer for academic reports
# Uses local TinyTeX (pdflatex + bibtex + latexmk), no Docker needed.
#
# Usage:
#   ./render.sh              Render main.pdf in default latex/ dir
#   ./render.sh /path/to/tex  Render main.pdf in specified folder
#   ./render.sh --clean       Remove build artifacts
#   ./render.sh --watch       Live preview (rebuild on file changes)
#   ./render.sh --deps        Install missing TeX packages for this document
#   ./render.sh --output /tmp Build and copy PDF to specified location
#
# Modes:
#   (default)  Full pdflatex → bibtex → pdflatex×2 → glossary → pdflatex×2
#   --clean    Remove .aux .log .out .toc .lof .lot .bbl .blg .run.xml .nav .snm .fls .fdb_latexmk
#   --watch    Live preview with latexmk -pvc (Ctrl+C to stop)
#   --deps     Install missing TeX packages via tlmgr
#   --output   Copy final PDF to specified path after build
#   --force    Continue past non-fatal warnings (unresolved refs, duplicate labels)

set -euo pipefail

# ── Configuration ──────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_TEX_DIR="${SCRIPT_DIR}/latex"
OUTPUT_DIR="${SCRIPT_DIR}"
TEX_DIR=""
MODE="render"
OUTPUT_PATH=""
MAX_PASSES=5

# ── Parse arguments ────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --clean|-c)   MODE="clean"; shift ;;
        --watch|-w)   MODE="watch"; shift ;;
        --deps|-d)    MODE="deps"; shift ;;
        --force|-f)   FORCE_MODE="true"; shift ;;
        --output|-o)  OUTPUT_PATH="$2"; shift 2 ;;
        --help|-h)
            sed -n '2,17p' "$0"
            exit 0
            ;;
        -*)
            echo "Unknown flag: $1" >&2
            exit 1
            ;;
        *)
            TEX_DIR="$1"
            shift
            ;;
    esac
done

TEX_DIR="${TEX_DIR:-$DEFAULT_TEX_DIR}"

if [[ ! -d "$TEX_DIR" ]]; then
    echo "Error: TeX directory not found: $TEX_DIR" >&2
    exit 1
fi

if [[ ! -f "$TEX_DIR/main.tex" ]]; then
    echo "Error: main.tex not found in $TEX_DIR" >&2
    exit 1
fi

# ── Check toolchain ────────────────────────────────────────────
check_tools() {
    local missing=()
    for cmd in pdflatex bibtex latexmk tlmgr; do
        if ! command -v "$cmd" &>/dev/null; then
            missing+=("$cmd")
        fi
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "Error: Missing tools: ${missing[*]}" >&2
        echo "Install TinyTeX: curl -sL https://yihui.org/tinytex/install | sh" >&2
        exit 1
    fi
}

# ── Clean mode ─────────────────────────────────────────────────
do_clean() {
    echo "Cleaning build artifacts in $TEX_DIR..."
    local exts="aux log out toc lof lot bbl blg run.xml nav snm fls fdb_latexmk glo gls glg ist xdy synctex.gz"
    for ext in $exts; do
        rm -f "$TEX_DIR"/*."$ext"
    done
    # Clean subfile aux files in Chapter/ and chapter/
    for d in Chapter chapter; do
        if [[ -d "$TEX_DIR/$d" ]]; then
            rm -f "$TEX_DIR/$d"/*.aux
        fi
    done
    echo "Done."
}

# ── Deps mode ──────────────────────────────────────────────────
do_deps() {
    echo "Checking for missing TeX packages needed by this document..."
    cd "$TEX_DIR"

    # Scan all .tex files for \usepackage{...} directives
    local pkgs
    pkgs=$(grep -rhoP '\\usepackage(?:\[.*?\])?\{\K[^}]+' --include='*.tex' . 2>/dev/null | sort -u)

    local missing=()
    for pkg in $pkgs; do
        if ! kpsewhich "${pkg}.sty" &>/dev/null; then
            missing+=("$pkg")
        fi
    done

    if [[ ${#missing[@]} -eq 0 ]]; then
        echo "All required packages are installed."
        return 0
    fi

    echo "Missing packages: ${missing[*]}"
    echo "Installing..."

    # Map package names to tlmgr package names (common mismatches)
    declare -A PKG_MAP=(
        [vietnam]="vntex"
        [glossary-superragged]="glossaries-extra"
        [titletoc]="titlesec"
        [tocbasic]="koma-script"
        [subcaption]="caption"
    )

    for pkg in "${missing[@]}"; do
        local tlpkg="${PKG_MAP[$pkg]:-$pkg}"
        echo "  Installing $tlpkg..."
        tlmgr install "$tlpkg" 2>&1 || echo "    Warning: could not install $tlpkg (may already be bundled)"
    done
    echo "Done. Re-run render.sh to compile."
}

# ── Render mode ────────────────────────────────────────────────
do_render() {
    echo "Rendering $TEX_DIR/main.tex ..."
    cd "$TEX_DIR"

    # Clean aux from previous runs for clean state
    rm -f main.aux main.bbl main.blg

    local latexmk_opts="-pdf -interaction=nonstopmode"
    if [[ "${FORCE_MODE:-}" == "true" ]]; then
        latexmk_opts="$latexmk_opts -f"
    fi

    if latexmk $latexmk_opts main.tex; then
        local pdf_size
        pdf_size=$(du -h main.pdf | cut -f1)
        echo "Success: main.pdf ($pdf_size, $(pdfinfo main.pdf 2>/dev/null | grep Pages | awk '{print $2}') pages)"

        if [[ -n "${OUTPUT_PATH:-}" ]]; then
            cp main.pdf "$OUTPUT_PATH"
            echo "Copied to: $OUTPUT_PATH"
        fi
    else
        echo "Build completed with warnings (PDF may still be usable)." >&2
        if [[ -f main.pdf ]]; then
            echo "Check main.log for details. Using -f flag to force."
            # Force one more complete cycle
            pdflatex -interaction=nonstopmode main.tex > /dev/null 2>&1 || true
            bibtex main > /dev/null 2>&1 || true
            pdflatex -interaction=nonstopmode main.tex > /dev/null 2>&1 || true
            pdflatex -interaction=nonstopmode main.tex > /dev/null 2>&1 || true
            pdflatex -interaction=nonstopmode main.tex > /dev/null 2>&1 || true

            if [[ -f main.pdf ]]; then
                local pdf_size
                pdf_size=$(du -h main.pdf | cut -f1)
                echo "Forced build: main.pdf ($pdf_size)"

                if [[ -n "${OUTPUT_PATH:-}" ]]; then
                    cp main.pdf "$OUTPUT_PATH"
                    echo "Copied to: $OUTPUT_PATH"
                fi
            fi
        fi
        # Check for LaTeX errors vs warnings
        if grep -q "^!" main.log; then
            echo "LaTeX errors found:"
            grep "^!" main.log | head -5
            return 1
        fi
    fi
}

# ── Watch mode ─────────────────────────────────────────────────
do_watch() {
    echo "Starting live preview for $TEX_DIR/main.tex ..."
    echo "Press Ctrl+C to stop."
    cd "$TEX_DIR"
    latexmk -pvc -pdf -interaction=nonstopmode main.tex
}

# ── Main ───────────────────────────────────────────────────────
check_tools

case "$MODE" in
    clean)  do_clean ;;
    deps)   do_deps ;;
    watch)  do_watch ;;
    render)
        do_clean
        do_render
        ;;
esac
