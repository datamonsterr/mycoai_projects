import JSZip from 'jszip'
import { api } from '@/services/api-client'

/**
 * Template ZIP for batch index/retrieve data upload.
 * Users download this template as a ZIP folder, organize images
 * following the structure, and upload back.
 */

// Legacy CSV template (kept for backward compatibility with Retrieve page)
export const INDEX_TEMPLATE_CSV = `strain_name,species_name,media_name,image_path
# Example (remove this line):
# T379,thymicola,MEA,/path/to/image1.jpg
# T379,thymicola,PDA,/path/to/image2.jpg
# T362,sclerotigenum,MEA,/path/to/image3.jpg
`

export const TEMPLATE_AGENTS_MD = `# MycoAI Retrieve Species — Batch Instructions

## Overview
For species retrieval, download the ZIP template below and organize your plate images
into strain-named folders under an "images/" directory. Each strain folder contains
images of that strain grown on specific media. The system will segment each image
using K-means clustering and retrieve the closest matching species via Qdrant.

## Directory Structure (inside ZIP)
\`\`\`
mycoai_retrieval_batch/
├── AGENTS.md          # This file — pre-instruction agent file
├── images/
│   ├── T379/
│   │   ├── T379_MEA.jpg
│   │   └── T379_CYA.jpg
│   └── T362/
│       ├── T362_MEA.jpg
│       └── T362_DG18.jpg
\`\`\`

## Instructions
1. Download the ZIP template from the Retrieve Species page
2. Unzip it to a working directory
3. Create a subfolder for each strain under images/
4. Place plate images in the correct strain folder
5. Edit AGENTS.md with any custom instructions (optional)
6. Re-zip the entire folder (including AGENTS.md)
7. Upload the ZIP via "Batch Upload (ZIP)" on the Retrieve Species page
8. The system will auto-segment and retrieve matching species

## Supported Media
MEA, CYA, YES, DG18, CREA, OA, M40Y

## Accepted Image Formats
.jpg, .jpeg, .png
`

export function downloadTemplate(filename: string, content: string) {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export function downloadAgentsMd() {
  const blob = new Blob([TEMPLATE_AGENTS_MD], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'AGENTS.md'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}


export const AGENTS_MD_CONTENT = `# MycoAI Index New Data — Batch Instructions

## Goal
Prepare a ZIP for a data owner to add new indexed training data. This is not for the Retrieve Species user flow.

## Directory Structure
\`\`\`
mycoai_batch/
├── AGENTS.md
├── metadata.json
└── images/
    ├── T379/
    │   ├── T379_MEA.jpg
    │   └── T379_CYA.jpg
    └── T362/
        ├── T362_MEA.jpg
        └── T362_DG18.jpg
\`\`\`

## metadata.json
Map each strain folder to species and optional notes:
\`\`\`json
{
  "strains": {
    "T379": { "species": "thymicola", "media": ["MEA", "CYA"], "notes": "example" },
    "T362": { "species": "sclerotigenum", "media": ["MEA", "DG18"] }
  }
}
\`\`\`

## Local Agent Task
1. Normalize raw plate images into \`images/{strain}/\` folders.
2. Fill \`metadata.json\` so every strain folder has a species mapping.
3. Rename files to include media when known, e.g. \`T379_MEA.jpg\`.
4. Keep only .jpg, .jpeg, or .png files.
5. Zip the \`mycoai_batch/\` folder and upload it on Index New Data.

## Supported Media
MEA, CYA, YES, DG18, CREA, OA, M40Y

## Upload Result
MycoAI reads metadata, uploads images, auto-segments plates, then indexes segments into Qdrant.
`

const RENAME_SCRIPT = `#!/usr/bin/env bash
# Helper script to rename images in strain folders to include strain prefix.
# Usage: bash scripts/rename_images.sh
#
# This script renames files like "image1.jpg" to "T379_image1.jpg"
# based on the parent folder name (strain identifier).

set -euo pipefail

IMAGES_DIR="$(dirname "$0")/../images"

if [ ! -d "$IMAGES_DIR" ]; then
    echo "Error: images/ directory not found"
    exit 1
fi

find "$IMAGES_DIR" -type f \\( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \\) | while read -r file; do
    strain=$(basename "$(dirname "$file")")
    base=$(basename "$file")
    # Skip if already prefixed with strain
    if [[ "$base" != \${strain}_* ]]; then
        newname="\${strain}_\${base}"
        mv "$file" "$(dirname "$file")/$newname"
        echo "Renamed: $base -> $newname"
    fi
done

echo "Done."
`

export async function downloadTemplateZip(): Promise<void> {
  const zip = new JSZip()

  const root = zip.folder('mycoai_batch')!
  root.file('AGENTS.md', AGENTS_MD_CONTENT)

  const scripts = root.folder('scripts')!
  scripts.file('rename_images.sh', RENAME_SCRIPT)

  root.file('metadata.json', JSON.stringify({
    strains: {
      T379: { species: 'thymicola', media: ['MEA', 'CYA'], notes: 'example strain' },
      T362: { species: 'sclerotigenum', media: ['MEA', 'DG18'] },
    },
  }, null, 2))

  const images = root.folder('images')!
  const t379 = images.folder('T379')!
  t379.file('T379_MEA.jpg.example', '')
  t379.file('T379_CYA.jpg.example', '')

  const t362 = images.folder('T362')!
  t362.file('T362_MEA.jpg.example', '')
  t362.file('T362_DG18.jpg.example', '')

  images.file('README.md', `# Images folder

Organize your data as:
  images/{strain_name}/{strain}_{media}.jpg

Species and extra strain information belong in ../metadata.json.
Accepted image formats: .jpg, .jpeg, .png.`)

  const blob = await zip.generateAsync({ type: 'blob' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'mycoai_batch_template.zip'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export async function uploadBatchZip(
  zipFile: File,
  options?: { defaultMedia?: string; defaultSpecies?: string; method?: string },
): Promise<{
  status: string
  batch_name: string
  total: number
  successful: number
  failed: number
  results: Array<{
    image_id: string
    strain: string
    media: string
    species: string
    segments: number
    filename: string
  }>
  errors: Array<{ file: string; error: string }>
}> {
  const formData = new FormData()
  formData.append('zipfile', zipFile)
  if (options?.defaultMedia) formData.append('default_media', options.defaultMedia)
  if (options?.defaultSpecies) formData.append('default_species', options.defaultSpecies)
  if (options?.method) formData.append('method', options.method)

  return api.post('/images/batch-zip', formData)
}
