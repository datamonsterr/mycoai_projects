from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from qdrant_client import QdrantClient

RESULTS_DIR = Path("/home/dat/dev/mycoai_projects/results")
THRESHOLD_DIR = RESULTS_DIR / "threshold"
THRESHOLD_DIR.mkdir(parents=True, exist_ok=True)
GRAD_FIG = Path("/home/dat/dev/mycoai_projects/graduation_report/report/figures")
LATEX_FIG = Path("/home/dat/dev/mycoai_projects/docs/graduation_report/latex/figures")
GRAD_FIG.mkdir(parents=True, exist_ok=True)
LATEX_FIG.mkdir(parents=True, exist_ok=True)

KNOWN_SPECIES = {
    "penicillium-aurantiogriseum", "penicillium-cyclopium",
    "penicillium-freii", "penicillium-melanoconidium",
    "penicillium-neoechinulatum", "penicillium-polonicum",
    "penicillium-tricolor", "penicillium-viridicatum",
}
KNOWN_DISPLAY = [s.replace("penicillium-", "").replace("-", " ") for s in sorted(KNOWN_SPECIES)]


def is_known_species(specy: str) -> bool:
    return specy.strip().lower() in {s.replace("-", " ") for s in KNOWN_SPECIES}


def write():
    client = QdrantClient(url="http://127.0.0.1:6333", timeout=120)

    species_strains = defaultdict(list)
    points, _ = client.scroll(collection_name="full_prepared_features", limit=3000, with_payload=True)
    for p in points:
        pl = p.payload or {}
        species = (pl.get("species") or pl.get("specy") or "").strip().lower()
        strain = (pl.get("strain") or "").strip()
        species_strains[species].append(strain)

    mapping_df = pd.read_csv(Path("/home/dat/dev/mycoai_projects/Dataset/strain_to_specy.csv"))
    strain_to_specy = dict(zip(mapping_df["Strain"], mapping_df["Species"]))
    canonical_lookup = {s.replace("penicillium ", "").replace(" ", "-").lower(): s for s in mapping_df["Species"].unique()}

    known_dict = {}
    for species_slug in sorted(species_strains):
        strains = species_strains[species_slug]
        if strains:
            strain = strains[0]
            if is_known_species(species_slug):
                canonical = canonical_lookup.get(species_slug, species_slug)
                known_dict[canonical] = strain

    rows = []
    for species in sorted(known_dict):
        rows.append({"species": species, "strain": known_dict[species], "is_known": 1})
    for species_slug in sorted(species_strains):
        if not is_known_species(species_slug):
            strains = species_strains[species_slug]
            if strains:
                rows.append({"species": species_slug, "strain": strains[0], "is_known": 0})

    df = pd.DataFrame(rows)
    df.to_csv(THRESHOLD_DIR / "known_unknown_strains.csv", index=False)

    known_count = int(df["is_known"].sum())
    unknown_count = len(df) - known_count

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(["Known", "Unknown"], [known_count, unknown_count], color=["#2ecc71", "#e74c3c"])
    for i, v in enumerate([known_count, unknown_count]):
        ax.text(i, v + 0.5, str(v), ha="center", fontsize=12, fontweight="bold")
    ax.set_ylabel("Number of species"); ax.set_title("Full-prepared dataset: known vs unknown species")
    for out in [GRAD_FIG / "threshold_known_unknown_distribution.png", LATEX_FIG / "threshold_known_unknown_distribution.png"]:
        fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)

    species_counts = pd.Series([r["species"] for r in rows])
    known_species_list = [r["species"] for r in rows if r["is_known"]]
    fig, ax = plt.subplots(figsize=(12, 6))
    counts = species_counts.value_counts().head(20)
    colors = ["#2ecc71" if sp in known_species_list else "#e74c3c" for sp in counts.index]
    ax.bar(range(len(counts)), counts.values, color=colors)
    for i, (sp, c) in enumerate(zip(counts.index, counts.values)):
        ax.text(i, c + 0.3, str(c), ha="center", fontsize=8)
    ax.set_xticks(range(len(counts))); ax.set_xticklabels(counts.index, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Count"); ax.set_title("Species distribution in full_prepared dataset")
    for out in [GRAD_FIG / "threshold_full_species_distribution.png", LATEX_FIG / "threshold_full_species_distribution.png"]:
        fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(json.dumps({"known": known_count, "unknown": unknown_count, "csv": str(THRESHOLD_DIR / "known_unknown_strains.csv")}))


if __name__ == "__main__":
    write()
