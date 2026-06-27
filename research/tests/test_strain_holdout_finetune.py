from pathlib import Path

import torch
from src.experiments.finetune_dl.train_strain_holdout import (
    collect_segment_paths,
    resolve_weights_root,
    set_reproducible_seed,
)


def test_collect_segment_paths_filters_by_segment_method(tmp_path: Path) -> None:
    yolo = tmp_path / "species-a" / "dto-100-a1" / "mea" / "ob" / "segments_yolo" / "segment_1.jpg"
    kmeans = tmp_path / "species-a" / "dto-100-a1" / "mea" / "ob" / "segments_kmeans" / "segment_1.jpg"
    yolo.parent.mkdir(parents=True)
    kmeans.parent.mkdir(parents=True)
    yolo.write_bytes(b"yolo")
    kmeans.write_bytes(b"kmeans")

    yolo_map = collect_segment_paths(tmp_path, segment_method="yolo")
    kmeans_map = collect_segment_paths(tmp_path, segment_method="kmeans")

    assert list(yolo_map) == ["DTO 100-A1"]
    assert yolo_map["DTO 100-A1"] == [yolo]
    assert kmeans_map["DTO 100-A1"] == [kmeans]


def test_resolve_weights_root_is_method_specific(tmp_path: Path) -> None:
    assert resolve_weights_root(tmp_path, "yolo") == tmp_path / "yolo_finetuned"
    assert resolve_weights_root(tmp_path, "kmeans") == tmp_path / "kmeans_finetuned"


def test_set_reproducible_seed_sets_torch_flags() -> None:
    set_reproducible_seed(7)

    import torch

    assert torch.initial_seed() == 7
    assert torch.backends.cudnn.deterministic is True
    assert torch.backends.cudnn.benchmark is False
