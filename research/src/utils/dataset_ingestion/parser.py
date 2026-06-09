"""
Parser: extracts species, strain, media, and angle from messy filenames.

Typical patterns found in Dataset/new_data/:
  - "mononematosum CBS 172_87 CYAo.jpg"  → species, strain_code, media+angle
  - "nordicum IBT 5105 MEAo.jpg"
  - "scabrosum T491 MEA rev.JPG"         → media + angle separated
  - "T379 MEA ob.jpg"                     → strain_code only, media+angle
  - "DSCN2477.JPG"                        → no metadata in filename

Folder structure gives species → strain grouping:
  {alpha_group}/{species_name}/{strain_code}/{files...}
"""

from __future__ import annotations

import re
from dataclasses import dataclass


MEDIA_PATTERNS: dict[str, str] = {
    "cya": "CYA",
    "mea": "MEA",
    "yes": "YES",
    "dg18": "DG18",
    "crea": "CREA",
    "oa": "OA",
    "m40y": "M40Y",
}

ANGLE_O: str = "ob"
ANGLE_R: str = "rev"


@dataclass
class SpeciesStrainInfo:
    species_name: str
    strain_code: str
    media: str | None = None
    angle: str | None = None
    original_filename: str = ""


def parse_image_filename(
    filename: str,
    species_from_folder: str | None = None,
    strain_from_folder: str | None = None,
) -> SpeciesStrainInfo:
    """Parse species, strain, media, angle from a single image filename.

    Tries three strategies in order:
      1) full pattern: species strain media angle (with space-separated angle)
      2) compact pattern: species strain media[or] (angle suffix on media)
      3) strain-only: strain media angle (species comes from folder)
      4) fallback: species and strain from folder, media/angle UNKNOWN
    """
    base = filename.rsplit(".", 1)[0].strip()
    lower = base.lower()

    media = None
    angle = None
    species_from_name: str | None = None
    strain_from_name: str | None = None

    # Strategy 1: "MEDIA ANGLE" pattern (space-separated)
    # e.g., "scabrosum T491 MEA rev" → species=scabrosum, strain=T491, media=MEA, angle=rev
    m_angle = re.search(
        r"(cya|mea|yes|dg18|crea|oa|m40y)\s+(ob|rev)\b", lower
    )
    if m_angle:
        media = MEDIA_PATTERNS[m_angle.group(1)]
        angle = m_angle.group(2)
        rest = lower[: m_angle.start()].strip()
        species_from_name, strain_from_name = _parse_species_strain(rest)

    # Strategy 2: "MEDIA[or]" suffix pattern (compact)
    # e.g., "mononematosum CBS 172_87 CYAo" → media=CYA, angle=ob
    if media is None:
        m_suffix = re.search(r"\b(cya|mea|yes|dg18|crea|oa|m40y)(o|r)\b", lower)
        if m_suffix:
            media = MEDIA_PATTERNS[m_suffix.group(1)]
            angle = ANGLE_O if m_suffix.group(2) == "o" else ANGLE_R
            rest = lower[: m_suffix.start()].strip()
            species_from_name, strain_from_name = _parse_species_strain(rest)

    # Strategy 3: "MEDIA[or]" as final word
    # e.g., "CYAo" at the end
    if media is None:
        words = lower.split()
        for word in reversed(words):
            m_final = re.match(r"^(cya|mea|yes|dg18|crea|oa|m40y)(o|r)$", word)
            if m_final:
                media = MEDIA_PATTERNS[m_final.group(1)]
                angle = ANGLE_O if m_final.group(2) == "o" else ANGLE_R
                rest = " ".join(words[: words.index(word.split()[0] if len(words) > 1 else word)])
                species_from_name, strain_from_name = _parse_species_strain(lower.replace(word, "").strip())
                break

    # Fallback: use folder context
    species = species_from_name or species_from_folder or "unknown"
    strain = strain_from_name or strain_from_folder or "unknown"

    return SpeciesStrainInfo(
        species_name=species,
        strain_code=strain,
        media=media or "unknown",
        angle=angle or "unknown",
        original_filename=filename,
    )


def _parse_species_strain(text: str) -> tuple[str | None, str | None]:
    """Extract species name and strain code from text.

    Strain codes can be multi-token: CBS 172_87, IBT 5105, DTO 148-D1.
    Use a greedy regex to find the strain code region.
    Returns (species_or_None, strain_or_None)
    """
    text = text.strip()
    if not text:
        return None, None

    # Match known strain patterns (multi-token)
    # CBS/IBT/NRRL followed by numbers/underscores/slashes
    # DTO followed by numbers/dashes/letters
    # T followed by numbers
    # Plain numbers (rare fallback)
    m = re.search(
        r"\b(T\d+)\b"
        r"|\b(CBS\s+[\d_/]+)\b"
        r"|\b(IBT\s+\d+)\b"
        r"|\b(DTO\s+[\d\-A-Za-z]+)\b"
        r"|\b(NRRL\s+\d+)\b",
        text,
        re.IGNORECASE,
    )

    if not m:
        return text, None

    span_start, span_end = m.span()
    species_part = text[:span_start].strip()
    strain_code = text[span_start:span_end].strip()

    return (species_part if species_part else None), strain_code.upper()


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------
_TEST_CASES: list[tuple[str, str | None, str | None, str, str]] = [
    (
        "mononematosum CBS 172_87 CYAo.jpg",
        "mononematosum",
        "CBS 172_87",
        "CYA",
        "ob",
    ),
    (
        "nordicum IBT 5105 MEAo.jpg",
        "nordicum",
        "IBT 5105",
        "MEA",
        "ob",
    ),
    (
        "nordicum IBT 5105 CYAr.jpg",
        "nordicum",
        "IBT 5105",
        "CYA",
        "rev",
    ),
    (
        "T491 MEA rev.JPG",
        None,
        "T491",
        "MEA",
        "rev",
    ),
    (
        "T491 CYA ob.JPG",
        None,
        "T491",
        "CYA",
        "ob",
    ),
    (
        "DSCN2477.JPG",
        None,
        None,
        "unknown",
        "unknown",
    ),
    (
        "T379 MEA ob.jpg",
        None,
        "T379",
        "MEA",
        "ob",
    ),
    (
        "paecilomyceforme CBS 160_42 CYAr.jpg",
        "paecilomyceforme",
        "CBS 160_42",
        "CYA",
        "rev",
    ),
]


def run_parser_tests() -> bool:
    all_pass = True
    for filename, exp_species, exp_strain, exp_media, exp_angle in _TEST_CASES:
        result = parse_image_filename(filename)
        ok = True
        if exp_species is not None and result.species_name.lower() != exp_species.lower():
            ok = False
        if exp_strain is not None and result.strain_code.lower() != exp_strain.lower():
            ok = False
        if result.media != exp_media:
            ok = False
        if result.angle != exp_angle:
            ok = False
        if not ok:
            all_pass = False
            print(
                f"FAIL: {filename!r}\n"
                f"  expected: species={exp_species}, strain={exp_strain}, "
                f"media={exp_media}, angle={exp_angle}\n"
                f"  got:      species={result.species_name}, strain={result.strain_code}, "
                f"media={result.media}, angle={result.angle}"
            )
    return all_pass


if __name__ == "__main__":
    ok = run_parser_tests()
    print("All parser tests passed" if ok else "Some tests FAILED")
    raise SystemExit(0 if ok else 1)
