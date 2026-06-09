"""
Scanner: walks messy dataset directory, extracts all metadata,
produces a structured DatasetManifest ready for DB ingestion.

Expected input structure (messy, Dataset/new_data/):
  {alpha_group}/
    {species_name}/
      {strain_code}/
        {image_files...}

Output: DatasetManifest with deduplicated species, media, and
a flat list of image entries with parsed metadata.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

try:
    from .parser import parse_image_filename
except ImportError:
    from src.utils.dataset_ingestion.parser import parse_image_filename

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".jpe", ".tif", ".tiff", ".bmp", ".webp"}
SKIP_FILES = {"thumbs.db", "desktop.ini", ".ds_store"}
ALPHA_GROUP_PATTERNS = {
    "A - C", "D - L", "M - R", "S - Z",
    "A-C", "D-L", "M-R", "S-Z",
    "A_-_C", "D_-_L", "M_-_R", "S_-_Z",
}


def _is_alpha_group(name: str) -> bool:
    return name.strip() in ALPHA_GROUP_PATTERNS


@dataclass
class ImageEntry:
    source_path: str
    species_name: str
    strain_code: str
    media_name: str
    angle: str
    original_filename: str


@dataclass
class DatasetManifest:
    species: set[str] = field(default_factory=set)
    media: set[str] = field(default_factory=set)
    images: list[ImageEntry] = field(default_factory=list)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(
            {
                "species": sorted(self.species),
                "media": sorted(self.media),
                "total_images": len(self.images),
                "images": [
                    {
                        "source_path": img.source_path,
                        "species_name": img.species_name,
                        "strain_code": img.strain_code,
                        "media_name": img.media_name,
                        "angle": img.angle,
                        "original_filename": img.original_filename,
                    }
                    for img in self.images
                ],
            },
            indent=indent,
        )

    def save(self, path: Path) -> None:
        path.write_text(self.to_json())


def scan_dataset(root: str | Path) -> DatasetManifest:
    """Walk the messy new_data directory and build a structured manifest.

    Handles multiple folder structures:
      1) {alpha}/{species}/{strain}/{files}    ← Dataset/new_data/
      2) {species}/{strain}/{files}             ← flat species grouping
      3) {strain} - {species}/{files}           ← old original/ format
    """
    root = Path(root)
    manifest = DatasetManifest()

    # Collect all image files first
    all_images: list[tuple[Path, list[str]]] = []
    for f in root.rglob("*"):
        if not f.is_file():
            continue
        if f.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        if f.name.lower() in SKIP_FILES:
            continue
        # Build folder context: parent chain from file up to root
        parts = list(f.relative_to(root).parts)
        all_images.append((f, parts))

    for filepath, parts in all_images:
        filename = filepath.name
        species_from_folder: str | None = None
        strain_from_folder: str | None = None

        # Detect structure type and extract species/strain from folders
        if len(parts) >= 3:
            # Possible structures:
            #   1) alpha_group/species/strain/file
            #   2) species/strain/sub/file
            # Identify alpha group folders
            grandparent = parts[-3] if len(parts) >= 3 else None
            parent_name = parts[-2]
            if grandparent and _is_alpha_group(grandparent):
                # Structure 1: alpha/species/strain/file
                species_from_folder = parent_name
                strain_from_folder = parts[-1].rsplit(".", 1)[0] if len(parts) == 3 else None
            elif len(parts) >= 3:
                # Structure 2: species/strain/(maybe substrain)/file
                species_from_folder = parts[-3]
                strain_from_folder = parts[-2]
        elif len(parts) == 2:
            # Structure: species/strain/file
            species_from_folder = parts[0]
            strain_from_folder = parts[1]
        elif len(parts) == 1:
            # Single file at root, parse from filename
            pass

        # Filter alpha groups from species detection
        if species_from_folder and _is_alpha_group(species_from_folder):
            species_from_folder = None

        # Also handle the old original/ format: "DTO 148-D1 Penicillium polonicum"
        parent_name = filepath.parent.name if filepath.parent != root else ""
        if "Penicillium" in parent_name or " - " in parent_name:
            # e.g., "DTO 478-C6 Penicillium viridicatum"
            m = __import__("re").match(
                r"(.+?)\s+(Penicillium\s+\w+)", parent_name
            )
            if m:
                strain_from_folder = m.group(1).strip()
                species_from_folder = m.group(2).strip()

        info = parse_image_filename(filename, species_from_folder, strain_from_folder)

        manifest.species.add(info.species_name)
        if info.media and info.media.lower() != "unknown":
            manifest.media.add(info.media)

        manifest.images.append(
            ImageEntry(
                source_path=str(filepath),
                species_name=info.species_name,
                strain_code=info.strain_code,
                media_name=info.media or "unknown",
                angle=info.angle or "unknown",
                original_filename=filename,
            )
        )

    return manifest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    root = sys.argv[1] if len(sys.argv) > 1 else "/home/dat/dev/mycoai_projects/Dataset/new_data"
    output = sys.argv[2] if len(sys.argv) > 2 else "/tmp/opencode/dataset_manifest.json"

    manifest = scan_dataset(root)
    manifest.save(Path(output))

    print(f"Species:  {len(manifest.species)}")
    print(f"Media:    {len(manifest.media)}")
    print(f"Images:   {len(manifest.images)}")
    print(f"Manifest: {output}")
