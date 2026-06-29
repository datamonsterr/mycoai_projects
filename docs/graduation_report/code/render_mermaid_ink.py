#!/usr/bin/env python3
"""Render mermaid .mmd files to PNG via mermaid.ink with neutral (grey) theme."""
from __future__ import annotations
import base64
import sys
import urllib.parse
import urllib.request
from pathlib import Path

def render(mmd_path: str, png_path: str, theme: str = "neutral") -> None:
    source = Path(mmd_path).read_text(encoding="utf-8")
    encoded = base64.standard_b64encode(source.encode("utf-8")).decode("ascii")
    encoded = urllib.parse.quote(encoded, safe="")
    url = f"https://mermaid.ink/img/{encoded}?theme={theme}&width=2400"
    print(f"Rendering {Path(mmd_path).name} ({len(source)} chars)...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    Path(png_path).write_bytes(data)
    sz = len(data)
    print(f"  -> {Path(png_path).name} ({sz} bytes)")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input.mmd> <output.png>")
        sys.exit(1)
    render(sys.argv[1], sys.argv[2])
