from __future__ import annotations

from collections import Counter
from typing import Any

from .models import AggregationResult

type AggregationStrategy = str


def aggregate_predictions(
    raw_results: list[dict[str, Any]],
    strain_to_specy: dict[str, str],
    k: int,
    strategy: AggregationStrategy = "weighted",
    species_weights: dict[str, dict[str, float]] | None = None,
) -> AggregationResult:
    species_scores: Counter[str] = Counter()
    species_counts: Counter[str] = Counter()

    for result in raw_results:
        for neighbor in result["neighbors"]:
            specy = neighbor.get("specy")
            score = neighbor.get("score", 0.0)
            extractor = neighbor.get("extractor", "")
            if not specy or specy == "unknown":
                strain = neighbor.get("strain")
                if strain:
                    specy = strain_to_specy.get(strain, "unknown")
            if specy and specy != "unknown":
                weight = 1.0
                if strategy == "manual_weighted" and species_weights:
                    wmap = species_weights.get(specy, {})
                    weight = wmap.get(extractor, 1.0)
                species_scores[specy] += score * weight
                species_counts[specy] += 1

    total_neighbors = sum(species_counts.values())
    ranked: list[tuple[str, float]] = []
    for specy, total_score in species_scores.items():
        if strategy == "weighted":
            final = total_score / total_neighbors if total_neighbors > 0 else 0.0
        elif strategy == "uni":
            final = (
                species_counts[specy] / total_neighbors if total_neighbors > 0 else 0.0
            )
        elif strategy == "manual_weighted":
            final = total_score / total_neighbors if total_neighbors > 0 else 0.0
        else:
            final = float(total_score)
        ranked.append((specy, final))

    ranked.sort(key=lambda x: x[1], reverse=True)
    top = ranked[0] if ranked else ("unknown", 0.0)

    return AggregationResult(
        top_species=top[0],
        top_score=round(top[1], 4),
        ranking=[
            AggregationResult.RankedEntry(species=s, score=round(sc, 4))
            for s, sc in ranked
        ],
    )
