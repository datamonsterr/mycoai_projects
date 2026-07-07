"""
Visualize threshold experiment predictions with PIL.
Categorizes each prediction and saves annotated query images.
"""

# ruff: noqa: E402
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Optional, Set

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from src.config import WORKSPACE_ROOT, RESULTS_DIR, CURATED_METADATA_PATH

CSV_PATH = RESULTS_DIR / "threshold" / "diverse_retrieval_results.csv"
OUTPUT_DIR = RESULTS_DIR / "threshold" / "viz"
MAX_PER_CATEGORY = 50


def _load_known_species() -> Set[str]:
    species: Set[str] = set()
    if not CURATED_METADATA_PATH.exists():
        return species
    with open(CURATED_METADATA_PATH) as f:
        curated = json.load(f)
    for item in curated:
        info = item.get("instance_info", item.get("data", {}))
        sp = info.get("species", "")
        if sp and sp.lower() != "unknown":
            species.add(sp.strip().lower())
            species.add(_strip_penicillium(sp).lower())
    return species


def _strip_penicillium(label: str) -> str:
    clean = label.strip().lower()
    for prefix in ("penicillium ",):
        if clean.startswith(prefix):
            return clean[len(prefix) :]
    return clean


def _is_known_species(predicted: str, known_species: Set[str]) -> bool:
    pred = predicted.strip().lower()
    return pred in known_species


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except IOError:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size)
        except IOError:
            return ImageFont.load_default()


def _categorize(row, known_species: Set[str]) -> Optional[str]:
    is_known = int(row["is_known"])
    true_label = str(row["species_label"])
    predicted = str(row["predicted_species"])
    if is_known == 1:
        true_stripped = _strip_penicillium(true_label)
        pred_stripped = _strip_penicillium(predicted)
        if true_stripped == pred_stripped:
            return "known_correct"
        else:
            return "known_incorrect"
    else:
        if _is_known_species(predicted, known_species):
            return "unknown_as_known"
        else:
            return "unknown_correct"


def visualize_one(row, category: str, known_species: Set[str], idx: int) -> None:
    img_path_rel = str(row["image_path"]).split(";")[0]
    img_path = WORKSPACE_ROOT / img_path_rel

    if not img_path.exists():
        print(f"  SKIP: image not found: {img_path}")
        return

    img = Image.open(img_path).convert("RGB")
    target_w, target_h = 512, 512
    img = img.resize((target_w, target_h))

    canvas = Image.new("RGB", (target_w, target_h + 120), (255, 255, 255))
    canvas.paste(img, (0, 0))

    draw = ImageDraw.Draw(canvas)
    font_title = _load_font(18)
    font_body = _load_font(14)
    font_small = _load_font(12)

    strain = str(row["strain"])
    true_label = str(row["species_label"])
    predicted = str(row["predicted_species"])
    confidence = float(row["predicted_confidence"])
    sample_id = str(row["sample_id"])
    is_known = int(row["is_known"])
    env = str(row.get("environment", ""))

    status_color = {
        "known_correct": (0, 128, 0),
        "known_incorrect": (255, 0, 0),
        "unknown_as_known": (255, 165, 0),
        "unknown_correct": (0, 0, 200),
    }

    color = status_color.get(category, (0, 0, 0))
    status_names = {
        "known_correct": "KNOWN_CORRECT",
        "known_incorrect": "KNOWN_INCORRECT",
        "unknown_as_known": "UNKNOWN_AS_KNOWN",
        "unknown_correct": "UNKNOWN_CORRECT",
    }

    y = target_h + 6
    lines = [
        (f"Status: {status_names[category]}", font_title, color),
        (f"Sample: {sample_id} | Env: {env}", font_body, (0, 0, 0)),
        (
            f"True: {true_label} | Predicted: {predicted} (conf: {confidence:.3f})",
            font_body,
            (0, 0, 0),
        ),
        (
            f"Strain: {strain} | Known: {'yes' if is_known else 'no'}",
            font_small,
            (100, 100, 100),
        ),
    ]

    for text, font, fill_color in lines:
        draw.text((10, y), text, fill=fill_color, font=font)
        y += font.size + 6

    s0_species = str(row.get("s0_species", ""))
    s1_species = str(row.get("s1_species", ""))
    s2_species = str(row.get("s2_species", ""))
    s3_species = str(row.get("s3_species", ""))
    s4_species = str(row.get("s4_species", ""))
    s0 = float(row.get("s0_score", 0) or 0)
    s1 = float(row.get("s1_score", 0) or 0)
    s2 = float(row.get("s2_score", 0) or 0)
    s3 = float(row.get("s3_score", 0) or 0)
    s4 = float(row.get("s4_score", 0) or 0)

    top5 = [
        (s0_species, s0),
        (s1_species, s1),
        (s2_species, s2),
        (s3_species, s3),
        (s4_species, s4),
    ]
    top5_str = " | ".join(f"{sp}({sc:.3f})" for sp, sc in top5 if sp)
    draw.text((10, y), f"Top-5: {top5_str}", fill=(80, 80, 80), font=font_small)

    out_dir = OUTPUT_DIR / category
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = (
        out_dir
        / f"{idx:03d}_{strain.replace(' ', '_').replace('/', '_')}_{sample_id[:60]}.jpg"
    )
    canvas.save(str(out_path), quality=85)


def main() -> None:
    known_species = _load_known_species()
    print(f"Loaded {len(known_species)} known species variants")

    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} entries from {CSV_PATH}")

    categories: Dict[str, list] = defaultdict(list)
    for _, row in df.iterrows():
        cat = _categorize(row, known_species)
        if cat:
            categories[cat].append(row)

    print("\nCategory counts (before limit):")
    for cat in [
        "known_correct",
        "known_incorrect",
        "unknown_as_known",
        "unknown_correct",
    ]:
        print(f"  {cat}: {len(categories[cat])}")

    for cat in categories:
        rows = categories[cat]
        limited = rows[:MAX_PER_CATEGORY]
        print(f"\nGenerating {len(limited)} visualizations for {cat}...")
        for i, row in enumerate(limited):
            visualize_one(row, cat, known_species, i)
            if (i + 1) % 25 == 0:
                print(f"  {i + 1}/{len(limited)}")

    print(f"\nDone. Visualizations saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
