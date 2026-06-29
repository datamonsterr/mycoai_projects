#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FIG_SRC = ROOT / "docs/graduation_report/latex/figures/src"
FIG_OUT = ROOT / "docs/graduation_report/latex/figures"
GEN_DIR = ROOT / "docs/graduation_report/code/drawio_generators"
DIAGRAMS = [
    {
        "generator": GEN_DIR / "generate_ch03_architecture.mjs",
        "source": FIG_SRC / "ch03_architecture.drawio",
    },
    {
        "generator": GEN_DIR / "generate_ch02_research_pipeline.mjs",
        "source": FIG_SRC / "ch02_research_pipeline.drawio",
    },
    {
        "generator": GEN_DIR / "generate_threshold_pipeline_diagram.mjs",
        "source": FIG_SRC / "threshold_pipeline_diagram.drawio",
    },
]


def run(cmd: list[str], label: str) -> None:
    print(f"[{label}]")
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def resolve_drawio_cli() -> str | None:
    env_cli = os.environ.get("DRAWIO_CLI")
    if env_cli:
        return env_cli
    for candidate in ("drawio", "draw.io", "diagrams.net"):
        path = shutil.which(candidate)
        if path:
            return path
    return None


def main() -> int:
    FIG_SRC.mkdir(parents=True, exist_ok=True)
    FIG_OUT.mkdir(parents=True, exist_ok=True)

    for diagram in DIAGRAMS:
        run(["node", str(diagram["generator"])], f"generate {Path(diagram['source']).name}")

    drawio_sources = [Path(diagram["source"]) for diagram in DIAGRAMS]
    missing_sources = [str(path) for path in drawio_sources if not path.exists()]
    if missing_sources:
        print("Missing generated .drawio sources:", file=sys.stderr)
        for path in missing_sources:
            print(f"- {path}", file=sys.stderr)
        return 1

    drawio_cli = resolve_drawio_cli()
    if drawio_cli:
        for src in drawio_sources:
            out = FIG_OUT / f"{src.stem}.png"
            run([drawio_cli, "--export", "--format", "png", "--output", str(out), str(src)], f"export {src.name}")
        return 0

    headless_script = ROOT / "docs/graduation_report/code/export_drawio_headless.cjs"
    if headless_script.is_file():
        print("draw.io CLI not found — falling back to headless Chromium export.", file=sys.stderr)
        run(["node", str(headless_script)], "headless export")
        return 0

    print("draw.io CLI not found. Generated .drawio sources only.", file=sys.stderr)
    print("Set DRAWIO_CLI, install drawio desktop, or ensure puppeteer + Chromium available.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
