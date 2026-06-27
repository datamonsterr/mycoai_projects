import torch

from src.experiments.finetune_dl.train_strain_holdout import build_finetune_model, run_strain_holdout_finetuning


def test_build_finetune_model_unfreezes_backbone() -> None:
    model = build_finetune_model("ResNet50", num_classes=3)
    trainable = [name for name, param in model.named_parameters() if param.requires_grad]

    assert trainable
    assert any(not name.startswith("fc.") for name in trainable)


def test_run_strain_holdout_defaults_to_patience_10(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "src.experiments.finetune_dl.train_strain_holdout.build_dataloaders",
        lambda **kwargs: ("train", "val", type("Enc", (), {"classes_": __import__('numpy').array([0, 1])})(), {"train_count": 1, "val_count": 1, "class_count": 2}),
    )
    monkeypatch.setattr(
        "src.experiments.finetune_dl.train_strain_holdout.build_finetune_model",
        lambda model_name, num_classes: type("Model", (), {"to": lambda self, device: self, "state_dict": lambda self: {}})(),
    )
    captured = {}

    def fake_train_model(**kwargs):
        captured["patience"] = kwargs["patience"]
        return {"history": {}, "best_val_accuracy": 0.0}

    monkeypatch.setattr("src.experiments.finetune_dl.train_strain_holdout.train_model", fake_train_model)
    monkeypatch.setattr("src.experiments.finetune_dl.train_strain_holdout.export_backbone_weights", lambda **kwargs: tmp_path / "w.pth")
    monkeypatch.setattr("src.experiments.finetune_dl.train_strain_holdout.torch.save", lambda *args, **kwargs: None)
    monkeypatch.setattr("src.experiments.finetune_dl.train_strain_holdout.resolve_weights_root", lambda *_: tmp_path)

    run_strain_holdout_finetuning(dataset_root=tmp_path, mapping_path=tmp_path / "m.csv")

    assert captured["patience"] == 10
