from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from backend.services import feature_extraction as backend_feature_extraction
from backend.services.feature_extraction import (
    _resolve_finetuned_weights,
    extract_features,
    extract_features_from_bytes,
)

pytestmark = [pytest.mark.integration]

COMPARISON_OUTPUT = Path("/tmp/opencode/effb1_vector_comparison.json")
FEATURES_JSON_PATH = Path("/tmp/opencode/segmented_features_effb1_test.json")


def _load_research_feature_rows(limit: int = 10) -> list[dict]:
    if not FEATURES_JSON_PATH.exists():
        pytest.skip(f"Research features JSON not found: {FEATURES_JSON_PATH}")
    rows = json.loads(FEATURES_JSON_PATH.read_text())
    selected = [
        row
        for row in rows
        if row.get("features", {}).get("efficientnetb1_finetuned", {}).get("vector")
    ][:limit]
    if len(selected) < limit:
        pytest.skip(
            f"Need {limit} rows with efficientnetb1_finetuned vectors, "
            f"got {len(selected)}"
        )
    return selected


def test_efficientnetb1_finetuned_vector_parity_for_10_segments() -> None:
    weights_path = _resolve_finetuned_weights("EfficientNetB1")
    if weights_path is None:
        pytest.skip("EfficientNetB1_finetuned weights not found")

    backend_feature_extraction._effnet_model = None
    rows = _load_research_feature_rows(limit=10)

    comparisons: list[dict[str, float | str]] = []
    cosine_distances: list[float] = []

    for row in rows:
        segment_path = Path("/home/dat/dev/mycoai") / row["segment_path"]
        if not segment_path.exists():
            continue

        backend_vectors = extract_features(segment_path)
        backend_vector = np.asarray(
            backend_vectors["efficientnetb1_finetuned"], dtype=np.float32
        )
        research_vector = np.asarray(
            row["features"]["efficientnetb1_finetuned"]["vector"], dtype=np.float32
        )
        if backend_vector.shape != research_vector.shape:
            raise AssertionError(
                f"Shape mismatch for {segment_path}: "
                f"{backend_vector.shape} vs {research_vector.shape}"
            )

        denom = (
            np.linalg.norm(backend_vector) * np.linalg.norm(research_vector)
        ) + 1e-8
        cosine_similarity = float(np.dot(backend_vector, research_vector) / denom)
        cosine_distance = 1.0 - cosine_similarity
        cosine_distances.append(cosine_distance)
        comparisons.append(
            {
                "segment_path": str(segment_path),
                "cosine_similarity": cosine_similarity,
                "cosine_distance": cosine_distance,
            }
        )

        bytes_vectors = extract_features_from_bytes(segment_path.read_bytes())
        bytes_vector = np.asarray(
            bytes_vectors["efficientnetb1_finetuned"], dtype=np.float32
        )
        np.testing.assert_allclose(bytes_vector, backend_vector, atol=1e-6, rtol=1e-5)

    if not cosine_distances:
        pytest.skip("No segment files from research features JSON were present locally")

    COMPARISON_OUTPUT.write_text(json.dumps(comparisons, indent=2))
    assert float(np.mean(cosine_distances)) < 0.01, comparisons
