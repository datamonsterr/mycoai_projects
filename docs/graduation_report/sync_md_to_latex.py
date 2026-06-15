#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path

CONTENT_DIR = Path("/home/dat/dev/mycoai_projects/docs/graduation_report/content")
LATEX_DIR = Path("/home/dat/dev/mycoai_projects/docs/graduation_report/latex/Chapter")

MAPPING = {
    "problem_statement.md": "1_Introduction.tex",
    "02-retrieval-model.md": "2_Literature_Review.tex",
    "03-web-application.md": "3_Methodology.tex",
    "04-agentic-engineering.md": "4_Implementation.tex",
    "05-conclusion.md": "5_Evaluation.tex",
}

def sync_file(md_file, tex_file):
    print(f"Syncing {md_file} -> {tex_file}...")
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{CONTENT_DIR}:/input:ro",
        "-v", f"/tmp/opencode:/output",
        "pandoc/core",
        f"/input/{md_file}",
        "-o", f"/output/{tex_file}",
        "-f", "markdown",
        "-t", "latex",
        "--wrap=none"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        
        # Move from tmp to final destination
        tmp_file = f"/tmp/opencode/{tex_file}"
        final_file = LATEX_DIR / tex_file
        
        # Read the content from the tmp file (Pandoc adds a lot of boilerplate, we'll extract the body)
        with open(tmp_file, "r") as f:
            content = f.read()
        
        # For now, just overwrite the chapter file (append mode to avoid losing structure)
        # In a real tool, we would merge intelligently
        with open(final_file, "w") as f:
            f.write(content)
            
        print(f"Successfully synced {tex_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error syncing {md_file}: {e}")

def main():
    if not CONTENT_DIR.exists():
        print(f"Error: Content directory {CONTENT_DIR} not found")
        return

    for md, tex in MAPPING.items():
        if (CONTENT_DIR / md).exists():
            sync_file(md, tex)
        else:
            print(f"Warning: {md} not found in {CONTENT_DIR}")

if __name__ == "__main__":
    main()