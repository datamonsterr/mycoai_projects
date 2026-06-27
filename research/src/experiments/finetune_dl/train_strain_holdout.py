from __future__ import annotations

import argparse
import copy
import json
import random
import shutil
from pathlib import Path
from typing import Dict, List

import numpy as np

import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from PIL import Image
from sklearn.preprocessing import LabelEncoder
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import EfficientNet_B1_Weights, MobileNet_V2_Weights, ResNet50_Weights

from src.config import ORIGINAL_PREPARED_DATASET_DIR, STRAIN_SPECIES_MAPPING_PATH, WEIGHTS_DIR
from src.experiments.finetune_dl.train_yolo_crops import export_backbone_weights
from torchvision.models import efficientnet_b1, mobilenet_v2, resnet50


def set_reproducible_seed(seed: int = 42) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


class SegmentClassificationDataset(Dataset):
    def __init__(self, paths: List[Path], labels: List[int], image_size: int, augment: bool) -> None:
        self.paths = [str(path) for path in paths]
        self.labels = labels
        normalize = transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ops = [transforms.Resize((image_size, image_size))]
        if augment:
            ops.extend([
                transforms.RandomHorizontalFlip(),
                transforms.RandomRotation(10),
                transforms.ColorJitter(brightness=0.1, contrast=0.1),
            ])
        ops.extend([transforms.ToTensor(), normalize])
        self.transform = transforms.Compose(ops)

    def __len__(self) -> int:
        return len(self.paths)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, int]:
        image = Image.open(self.paths[index]).convert("RGB")
        return self.transform(image), self.labels[index]


def build_finetune_model(model_name: str, num_classes: int) -> nn.Module:
    if model_name == "ResNet50":
        model = resnet50(weights=ResNet50_Weights.DEFAULT)
        num_features = model.fc.in_features
        model.fc = nn.Linear(num_features, num_classes)
        return model
    if model_name == "MobileNetV2":
        model = mobilenet_v2(weights=MobileNet_V2_Weights.DEFAULT)
        num_features = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(num_features, num_classes)
        return model
    if model_name == "EfficientNetB1":
        model = efficientnet_b1(weights=EfficientNet_B1_Weights.DEFAULT)
        num_features = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(num_features, num_classes)
        return model
    raise ValueError(f"Unsupported model: {model_name}")


def _strain_from_slug(strain_slug: str) -> str:
    parts = strain_slug.split("-")
    if len(parts) == 3:
        return f"{parts[0].upper()} {parts[1]}-{parts[2].upper()}"
    return strain_slug.replace("-", " ").upper()


def _species_from_slug(species_slug: str) -> str:
    return species_slug.replace("-", " ")


def collect_segment_paths(dataset_root: Path, segment_method: str) -> Dict[str, List[Path]]:
    segment_dir = f"segments_{segment_method}"
    strain_segments: Dict[str, List[Path]] = {}
    pattern = f"*/*/*/*/{segment_dir}/segment_*.jpg"
    for seg_path in sorted(dataset_root.glob(pattern)):
        parts = seg_path.relative_to(dataset_root).parts
        if len(parts) < 5:
            continue
        strain = _strain_from_slug(parts[1])
        strain_segments.setdefault(strain, []).append(seg_path)
    return strain_segments


def strain_to_species_from_original_prepared(dataset_root: Path) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for species_dir in dataset_root.iterdir():
        if not species_dir.is_dir():
            continue
        species = _species_from_slug(species_dir.name)
        for strain_dir in species_dir.iterdir():
            if not strain_dir.is_dir():
                continue
            mapping[_strain_from_slug(strain_dir.name)] = species
    return mapping


def resolve_weights_root(weights_dir: Path, segment_method: str) -> Path:
    return weights_dir / f"{segment_method}_finetuned"


def _bool_series(frame: pd.DataFrame) -> pd.Series:
    values = frame["Test"]
    if values.dtype == bool:
        return values
    return values.astype(str).str.lower().isin({"1", "true", "yes"})


def load_split_mapping(mapping_path: Path) -> tuple[set[str], Dict[str, str]]:
    frame = pd.read_csv(mapping_path)
    required = {"Strain", "Species", "Test"}
    if not required.issubset(frame.columns):
        missing = sorted(required.difference(frame.columns))
        raise ValueError(f"Missing mapping columns: {missing}")
    test_mask = _bool_series(frame)
    test_strains = set(frame.loc[test_mask, "Strain"].tolist())
    strain_to_species = dict(zip(frame["Strain"], frame["Species"]))
    return test_strains, strain_to_species


def build_dataloaders(
    dataset_root: Path,
    mapping_path: Path,
    segment_method: str,
    image_size: int,
    batch_size: int,
) -> tuple[DataLoader, DataLoader, LabelEncoder, dict[str, int]]:
    test_strains, csv_mapping = load_split_mapping(mapping_path)
    path_map = collect_segment_paths(dataset_root, segment_method)
    dir_mapping = strain_to_species_from_original_prepared(dataset_root)
    strain_to_species = {**dir_mapping, **csv_mapping}

    train_paths: List[Path] = []
    train_labels_raw: List[str] = []
    val_paths: List[Path] = []
    val_labels_raw: List[str] = []

    for strain, paths in path_map.items():
        species = strain_to_species.get(strain)
        if not species:
            continue
        if strain in test_strains:
            val_paths.extend(paths)
            val_labels_raw.extend([species] * len(paths))
        else:
            train_paths.extend(paths)
            train_labels_raw.extend([species] * len(paths))

    if not train_paths or not val_paths:
        raise ValueError("Empty train/validation split for requested segment method")

    encoder = LabelEncoder()
    encoder.fit(train_labels_raw + val_labels_raw)
    train_dataset = SegmentClassificationDataset(
        train_paths,
        encoder.transform(train_labels_raw).tolist(),
        image_size=image_size,
        augment=True,
    )
    val_dataset = SegmentClassificationDataset(
        val_paths,
        encoder.transform(val_labels_raw).tolist(),
        image_size=image_size,
        augment=False,
    )
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=2)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=1)
    counts = {
        "train_count": len(train_paths),
        "val_count": len(val_paths),
        "class_count": len(encoder.classes_),
    }
    return train_loader, val_loader, encoder, counts


def train_model(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    device: torch.device,
    epochs: int,
    learning_rate: float,
    patience: int,
) -> dict[str, object]:
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam([param for param in model.parameters() if param.requires_grad], lr=learning_rate)
    history: dict[str, list[float]] = {
        "train_loss": [],
        "train_accuracy": [],
        "val_loss": [],
        "val_accuracy": [],
    }
    best_state = copy.deepcopy(model.state_dict())
    best_val_acc = 0.0
    no_improve = 0

    for _ in range(epochs):
        for phase, loader in (("train", train_loader), ("val", val_loader)):
            model.train() if phase == "train" else model.eval()
            running_loss = 0.0
            running_correct = 0
            sample_count = 0
            for inputs, labels in loader:
                inputs = inputs.to(device)
                labels = labels.to(device)
                optimizer.zero_grad()
                with torch.set_grad_enabled(phase == "train"):
                    outputs = model(inputs)
                    loss = criterion(outputs, labels)
                    predictions = outputs.argmax(dim=1)
                    if phase == "train":
                        loss.backward()
                        optimizer.step()
                running_loss += loss.item() * inputs.size(0)
                running_correct += int((predictions == labels).sum().item())
                sample_count += inputs.size(0)
            epoch_loss = running_loss / max(sample_count, 1)
            epoch_acc = running_correct / max(sample_count, 1)
            history[f"{phase}_loss"].append(epoch_loss)
            history[f"{phase}_accuracy"].append(epoch_acc)
            if phase == "val":
                if epoch_acc >= best_val_acc:
                    best_val_acc = epoch_acc
                    best_state = copy.deepcopy(model.state_dict())
                    no_improve = 0
                else:
                    no_improve += 1
        if no_improve >= patience:
            break
    model.load_state_dict(best_state)
    return {"history": history, "best_val_accuracy": best_val_acc}


def run_strain_holdout_finetuning(
    dataset_root: Path = ORIGINAL_PREPARED_DATASET_DIR,
    mapping_path: Path = STRAIN_SPECIES_MAPPING_PATH,
    model_name: str = "ResNet50",
    segment_method: str = "yolo",
    epochs: int = 12,
    batch_size: int = 16,
    learning_rate: float = 1e-4,
    patience: int = 10,
    image_size: int = 224,
    clear_existing: bool = False,
) -> dict[str, object]:
    if segment_method not in {"yolo", "kmeans"}:
        raise ValueError(f"Unsupported segment_method: {segment_method}")

    set_reproducible_seed()

    train_loader, val_loader, encoder, counts = build_dataloaders(
        dataset_root=dataset_root,
        mapping_path=mapping_path,
        segment_method=segment_method,
        image_size=image_size,
        batch_size=batch_size,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_finetune_model(model_name, len(encoder.classes_)).to(device)
    train_result = train_model(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        device=device,
        epochs=epochs,
        learning_rate=learning_rate,
        patience=patience,
    )

    weights_root = resolve_weights_root(WEIGHTS_DIR, segment_method)
    if clear_existing and weights_root.exists():
        shutil.rmtree(weights_root)
    weights_root.mkdir(parents=True, exist_ok=True)

    backbone_path = export_backbone_weights(
        model=model,
        model_name=model_name,
        output_path=weights_root / f"{model_name}_finetuned.pth",
    )
    classifier_path = weights_root / f"{model_name}_classifier_checkpoint.pth"
    torch.save(model.state_dict(), classifier_path)
    classes_path = weights_root / f"{model_name}_classes.json"
    classes_path.write_text(json.dumps(encoder.classes_.tolist(), indent=2))
    summary = {
        "dataset_root": str(dataset_root),
        "mapping_path": str(mapping_path),
        "segment_method": segment_method,
        "model_name": model_name,
        "device": str(device),
        **counts,
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "best_val_accuracy": train_result["best_val_accuracy"],
        "backbone_weights_path": str(backbone_path),
        "classifier_checkpoint_path": str(classifier_path),
        "classes_path": str(classes_path),
        "history": train_result["history"],
    }
    summary_path = weights_root / f"{model_name}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    summary["summary_path"] = str(summary_path)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune backbone on original_prepared strain holdout segments")
    parser.add_argument("--dataset-root", type=Path, default=ORIGINAL_PREPARED_DATASET_DIR)
    parser.add_argument("--mapping-path", type=Path, default=STRAIN_SPECIES_MAPPING_PATH)
    parser.add_argument("--model-name", choices=["ResNet50", "MobileNetV2", "EfficientNetB1"], default="ResNet50")
    parser.add_argument("--segment-method", choices=["yolo", "kmeans"], default="yolo")
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--clear-existing", action="store_true")
    args = parser.parse_args()
    result = run_strain_holdout_finetuning(
        dataset_root=args.dataset_root,
        mapping_path=args.mapping_path,
        model_name=args.model_name,
        segment_method=args.segment_method,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        patience=args.patience,
        image_size=args.image_size,
        clear_existing=args.clear_existing,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
