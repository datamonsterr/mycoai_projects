#!/usr/bin/env bash
set -euo pipefail

LATEX_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Cleaning render artifacts..."
bash "$LATEX_DIR/clean.sh"

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
ZIP_NAME="graduation_report_${TIMESTAMP}.zip"
ZIP_PATH="/tmp/opencode/${ZIP_NAME}"

echo "Packaging $LATEX_DIR -> $ZIP_PATH..."
cd "$(dirname "$LATEX_DIR")"
python3 -c "
import shutil, os
from pathlib import Path
exclude = {'.aux','.bbl','.blg','.fdb_latexmk','.fls','.lof','.log','.lot','.out','.pdf','.run.xml','.toc','.synctex.gz','.synctex(busy)','.sh'}
LATEX = Path('$LATEX_DIR')
tmp = Path('/tmp/opencode/latex_pkg')
if tmp.exists():
    shutil.rmtree(tmp)
tmp.mkdir(parents=True)
for p in LATEX.rglob('*'):
    rel = p.relative_to(LATEX)
    # skip render artifacts and cache
    if p.suffix in exclude:
        continue
    if p.name == 'main-blx.bib':
        continue
    if '__pycache__' in p.parts or '.git' in p.parts:
        continue
    target = tmp / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    if p.is_file():
        shutil.copy2(p, target)
shutil.make_archive(str(Path('/tmp/opencode/graduation_report_${TIMESTAMP}').with_suffix('')), 'zip', tmp.parent, 'latex_pkg')
shutil.rmtree(tmp)
"

echo "Uploading to mycoai-data..."
MYCOAI_GDRIVE_REMOTE="${MYCOAI_GDRIVE_REMOTE:-mydrive:mycoai-data}"
REMOTE_DIR="graduation_report"
mise x -- rclone mkdir "${MYCOAI_GDRIVE_REMOTE}/${REMOTE_DIR}" 2>/dev/null || true
mise x -- rclone copy "$ZIP_PATH" "${MYCOAI_GDRIVE_REMOTE}/${REMOTE_DIR}/" --progress

echo "Uploaded: ${MYCOAI_GDRIVE_REMOTE}/${REMOTE_DIR}/${ZIP_NAME}"
rm -f "$ZIP_PATH"
echo "Done."
