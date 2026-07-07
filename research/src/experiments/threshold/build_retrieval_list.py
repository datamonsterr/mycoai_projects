#!/usr/bin/env python3
"""Build threshold experiment retrieval list.

Outputs results/threshold/threshold_retrieval_list.json mapping each image to
its metadata for classification (known test strains vs unknown diverse species).
"""

import csv
import json
from pathlib import Path
from collections import Counter

ROOT = Path("/home/dat/dev/mycoai_projects")
STRAIN_CSV = ROOT / "Dataset" / "strain_to_specy.csv"
INCOMING_JSON = ROOT / "Dataset" / "incoming_low_quality_metadata.json"
ORIG_PREPARED = ROOT / "Dataset" / "original_prepared"
FULL_PREPARED = ROOT / "Dataset" / "full_prepared"
OUTPUT_DIR = ROOT / "results" / "threshold"
OUTPUT_FILE = OUTPUT_DIR / "threshold_retrieval_list.json"

HELD_OUT_SUFFIXES = {
    "polonicum",
    "melanoconidium",
    "freii",
    "viridicatum",
    "tricolor",
    "neoechinulatum",
    "aurantiogriseum",
}

SEGMENT_TYPES = ["segments_kmeans", "segments_yolo"]
MAX_SEGMENTS_PER_SAMPLE = 3


def _species_suffix(species_name: str) -> str:
    """Return the species epithet (last word, lowercased)."""
    return species_name.lower().split()[-1]


def _is_held_out(species_simple: str) -> bool:
    """Check if a simple species name matches one of the 7 held-out species."""
    return species_simple.lower() in HELD_OUT_SUFFIXES


def _load_test_strains() -> list[dict]:
    """Parse strain_to_specy.csv, return list of Test=True strains."""
    strains = []
    with open(STRAIN_CSV, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Test", "").strip() == "True":
                strains.append(
                    {
                        "strain": row["Strain"].strip(),
                        "species_full": row["Species"].strip(),
                        "species_simple": _species_suffix(row["Species"]),
                        "strain_lower": row["Strain"].strip().lower().replace(" ", "-"),
                    }
                )
    return strains


def _collect_test_strain_entries(test_strains: list[dict]) -> list[dict]:
    """For each test strain, find segment images in original_prepared.

    Directory layout: original_prepared/penicillium-{simple}/{strain_lower}/{env}/{angle}/
    Inside the angle dir, prefer segments_kmeans/segment_*.jpg.
    """
    entries = []
    issues = []

    for ts in test_strains:
        sp_dir_name = f"penicillium-{ts['species_simple']}"
        strain_dir = ORIG_PREPARED / sp_dir_name / ts["strain_lower"]

        if not strain_dir.is_dir():
            issues.append(
                f"MISSING original_prepared dir for {ts['strain']}: {strain_dir}"
            )
            continue

        for env_dir in sorted(strain_dir.iterdir()):
            if not env_dir.is_dir():
                continue
            env = env_dir.name

            for angle_dir in sorted(env_dir.iterdir()):
                if not angle_dir.is_dir():
                    continue
                angle = angle_dir.name

                seg_files = _find_segment_images(angle_dir)
                if not seg_files:
                    issues.append(f"NO segments in {ts['strain']}/{env}/{angle}")
                    continue

                for i, seg_path in enumerate(seg_files[:MAX_SEGMENTS_PER_SAMPLE], 1):
                    sample_id = f"{ts['strain_lower']}_{env}_{angle}_seg{i}"
                    entries.append(
                        {
                            "sample_id": sample_id,
                            "strain": ts["strain"],
                            "species": ts["species_full"],
                            "is_known": True,
                            "environment": env,
                            "angle": angle,
                            "image_path": str(seg_path.relative_to(ROOT)),
                            "source": "test_strain",
                        }
                    )

    return entries, issues


def _find_segment_images(angle_dir: Path) -> list[Path]:
    """Find segment jpg images in angle dir, preferring segments_kmeans."""
    for seg_type in SEGMENT_TYPES:
        seg_dir = angle_dir / seg_type
        if seg_dir.is_dir():
            segs = sorted(seg_dir.glob("segment_*.jpg"))
            if segs:
                return segs
    return []


def _collect_incoming_entries() -> tuple[list[dict], list[str]]:
    """Parse incoming_low_quality_metadata.json, yield one entry per segment."""
    with open(INCOMING_JSON) as f:
        data = json.load(f)

    entries = []
    issues = []

    for item in data:
        info = item["instance_info"]
        species_simple = info["species"]
        strain = info["strain"]
        env = info["environment"]
        angle = info["angle"]
        item_id = item["item_id"]
        segments = item.get("paths", {}).get("segments", [])

        if not segments:
            issues.append(f"NO segments for {item_id}")
            continue

        is_known = _is_held_out(species_simple)

        for i, seg_rel in enumerate(segments[:MAX_SEGMENTS_PER_SAMPLE], 1):
            sample_id = f"{item_id}_seg{i}"
            entries.append(
                {
                    "sample_id": sample_id,
                    "strain": strain,
                    "species": species_simple,
                    "is_known": is_known,
                    "environment": env.lower(),
                    "angle": angle.lower(),
                    "image_path": seg_rel,
                    "source": "incoming",
                }
            )

    return entries, issues


def _validate_paths(entries: list[dict]) -> list[str]:
    """Check that each image_path exists on disk."""
    missing = []
    for e in entries:
        full_path = ROOT / e["image_path"]
        if not full_path.is_file():
            missing.append(e["image_path"])
    return missing


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    test_strains = _load_test_strains()
    print(f"Loaded {len(test_strains)} test strains (Test=True):")
    for ts in test_strains:
        print(f"  {ts['strain']} → {ts['species_full']}")

    test_entries, test_issues = _collect_test_strain_entries(test_strains)
    inc_entries, inc_issues = _collect_incoming_entries()

    all_entries = test_entries + inc_entries
    all_issues = test_issues + inc_issues

    known_count = sum(1 for e in all_entries if e["is_known"])
    unknown_count = sum(1 for e in all_entries if not e["is_known"])

    species_dist = Counter(e["species"] for e in all_entries)
    source_dist = Counter(e["source"] for e in all_entries)

    # Validate paths
    missing_paths = _validate_paths(all_entries)

    print(f"\nTotal entries: {len(all_entries)}")
    print(f"  Known (held-out):  {known_count}")
    print(f"  Unknown (diverse): {unknown_count}")
    print(f"  Source breakdown:   {dict(source_dist)}")
    print(f"\nSpecies distribution ({len(species_dist)} species):")
    for sp, cnt in species_dist.most_common():
        held = " [HELD-OUT]" if _is_held_out(sp) else ""
        print(f"  {sp}: {cnt}{held}")

    if missing_paths:
        print(f"\nMISSING image paths: {len(missing_paths)}")
        for mp in missing_paths[:10]:
            print(f"  {mp}")
        if len(missing_paths) > 10:
            print(f"  ... and {len(missing_paths) - 10} more")

    if all_issues:
        print(f"\nIssues ({len(all_issues)}):")
        for iss in all_issues[:15]:
            print(f"  {iss}")
        if len(all_issues) > 15:
            print(f"  ... and {len(all_issues) - 15} more")

    # Write output
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_entries, f, indent=2, ensure_ascii=False)

    print(f"\nWrote {len(all_entries)} entries to {OUTPUT_FILE}")

    if missing_paths:
        print(f"\nWARNING: {len(missing_paths)} image paths do not exist on disk!")
    else:
        print("All image paths validated.")


if __name__ == "__main__":
    main()
