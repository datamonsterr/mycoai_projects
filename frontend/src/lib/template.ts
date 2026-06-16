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


export const AGENTS_MD_CONTENT = `# MycoAI Batch Data Structure

## Overview
Organize your fungal plate images into strain-named folders under an "images/"
directory. Each strain folder contains one or more images of that strain grown on
specific media.

## Directory Structure
\`\`\`
mycoai_batch/
├── AGENTS.md          # This file
├── scripts/           # Helper scripts (if any)
│   └── rename_images.sh
└── images/
    ├── T379/
    │   ├── T379_MEA.jpg
    │   ├── T379_CYA.jpg
    │   └── T379_YES.jpg
    ├── T362/
    │   ├── T362_MEA.jpg
    │   └── T362_CREA.jpg
    └── ...
\`\`\`

## Naming Conventions
- **Strain folder**: Use the strain identifier (e.g., T379, DTO-148-C8)
- **Image filename**: Include strain and media in the filename for best
  auto-detection. Supported patterns:
  - \`{strain}_{media}.jpg\` (e.g., T379_MEA.jpg)
  - \`{strain} {media} ob.jpg\` (e.g., T379 MEA ob.jpg)
  - \`{strain} {media} rev.jpg\` (e.g., T379 CYA rev.jpg)
  - DTO format: \`DTO 148-C8 CYAob_edited.jpg\`

## Supported Media
MEA, CYA, YES, DG18, CREA, OA, M40Y

## Instructions
1. Download this template (ZIP file)
2. Unzip it to a working directory
3. Create a subfolder for each strain under \`images/\`
4. Place plate images in the correct strain folder
5. Re-zip the entire folder
6. Upload the ZIP via the "Upload Batch" section on the Index New Data page
7. The system will auto-segment and identify species

## Notes
- Species names matching existing database entries will be auto-linked
- Images are automatically segmented using K-means clustering
- Segments are indexed into Qdrant for visual similarity search
- Accepted formats: .jpg, .jpeg, .png
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

  // Example: species → strain → images structure
  const images = root.folder('images')!

  // thymicola / T379
  const thymicola = images.folder('thymicola')!
  thymicola.file('README.md', `# thymicola
Example species folder. Move your strain folders here.

Expected structure:
  images/thymicola/T379/T379_MEA.jpg
  images/thymicola/T379/T379_CYA.jpg
`)
  const t379 = thymicola.folder('T379')!
  t379.file('T379_MEA.jpg.example', '')
  t379.file('T379_CYA.jpg.example', '')
  t379.file('T379_YES.jpg.example', '')

  // sclerotigenum / T362
  const sclerotigenum = images.folder('sclerotigenum')!
  sclerotigenum.file('README.md', `# sclerotigenum
Example species folder. Move your strain folders here.
`)
  const t362 = sclerotigenum.folder('T362')!
  t362.file('T362_MEA.jpg.example', '')
  t362.file('T362_CREA.jpg.example', '')
  t362.file('T362_DG18.jpg.example', '')

  // Root-level README for the images/ folder
  images.file('README.md', `# Images folder

Organize your data as:
  images/{species_name}/{strain_name}/{strain}_{media}.jpg

Example:
  images/thymicola/T379/T379_MEA.jpg
  images/sclerotigenum/T362/T362_CYA.jpg

The species folder name is used to auto-link to existing species in the database.
The strain folder name is used as the strain identifier.
Media and species can also be parsed from the image filename.`)

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
