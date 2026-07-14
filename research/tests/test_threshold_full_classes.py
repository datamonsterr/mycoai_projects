import numpy as np

from src.experiments.threshold.full_classes import collect_six_sets, compute_confusion


def test_collect_six_sets_builds_expected_query_groups() -> None:
    candidates = []
    for env in ("CYA", "MEA"):
        for seg_idx in range(3):
            for angle in ("ob", "rev"):
                candidates.append(
                    {
                        "image_path_rel": f"{env}_{seg_idx}_{angle}.jpg",
                        "angle": angle,
                        "environment": env,
                        "segment_index": seg_idx,
                    }
                )
    test_sets = collect_six_sets(candidates)
    assert len(test_sets) == 6
    assert all(len(group) == 2 for group in test_sets)


def test_compute_confusion_uses_full_class_known_logic() -> None:
    rows = [
        {"is_known": 1, "predicted_species": "polonicum", "species_label": "Penicillium polonicum"},
        {"is_known": 1, "predicted_species": "freii", "species_label": "Penicillium polonicum"},
        {"is_known": 0, "predicted_species": "freii", "species_label": "expansum"},
        {"is_known": 0, "predicted_species": "freii", "species_label": "expansum"},
    ]
    scores = np.array([0.9, 0.9, 0.9, 0.1], dtype=float)
    metrics = compute_confusion(rows, scores, 0.5)
    assert metrics["tp"] == 1
    assert metrics["fn"] == 1
    assert metrics["fp"] == 1
    assert metrics["tn"] == 1
    assert round(metrics["f1"], 4) == 0.5
