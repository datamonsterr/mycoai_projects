"""Fold-specific EfficientNetB1 fine-tuning for Vast.ai.

Uses original_prepared YOLO segments + folds.csv for train/val splits.
Trains 5 folds sequentially, saves backbone weights to weights/.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from PIL import Image
from sklearn.preprocessing import LabelEncoder
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import EfficientNet_B1_Weights, efficientnet_b1
from tqdm import tqdm


# ── Paths ──────────────────────────────────────────────────────────────────
WORKSPACE = Path("/workspace")
DATASET = WORKSPACE / "Dataset"
ORIGINAL_PREPARED = DATASET / "original_prepared"
FOLDS_CSV = ORIGINAL_PREPARED / "folds.csv"
WEIGHTS = WORKSPACE / "weights"
WEIGHTS.mkdir(parents=True, exist_ok=True)

BATCH_SIZE = 16
NUM_EPOCHS = 60
LEARNING_RATE = 0.0001
PATIENCE = 12
HEIGHT = 256
WIDTH = 256
N_FOLDS = 5


# ── Dataset ────────────────────────────────────────────────────────────────


class SegmentDataset(Dataset):
    def __init__(self, paths: List[Path], labels: np.ndarray, transform=None):
        self.paths = [str(p) for p in paths]
        self.labels = labels
        self.transform = transform

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        image = Image.open(self.paths[idx]).convert("RGB")
        label = self.labels[idx]
        if self.transform:
            image = self.transform(image)
        return image, label


# ── Helpers ────────────────────────────────────────────────────────────────


def collect_segments() -> Dict[str, List[Path]]:
    """Map strain -> list of segment image paths."""
    strain_segments: Dict[str, List[Path]] = {}
    for seg_path in ORIGINAL_PREPARED.glob("*/*/*/*/segments_yolo/segment_*.jpg"):
        parts = seg_path.relative_to(ORIGINAL_PREPARED).parts
        if len(parts) < 6:
            continue
        strain_slug = parts[1]
        sp = strain_slug.split("-")
        strain = f"{sp[0].upper()} {sp[1]}-{sp[2].upper()}" if len(sp) == 3 else strain_slug.upper()
        strain_segments.setdefault(strain, []).append(seg_path)
    return strain_segments


def strain_to_species_from_original_prepared() -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for species_dir in ORIGINAL_PREPARED.iterdir():
        if not species_dir.is_dir():
            continue
        species = species_dir.name.replace("-", " ")
        for strain_dir in species_dir.iterdir():
            if not strain_dir.is_dir():
                continue
            parts = strain_dir.name.split("-")
            strain = f"{parts[0].upper()} {parts[1]}-{parts[2].upper()}" if len(parts) == 3 else strain_dir.name.upper()
            mapping[strain] = species
    return mapping


def build_dataloaders(
    strain_segments: Dict[str, List[Path]],
    strain_to_species: Dict[str, str],
    test_strains: List[str],
    batch_size: int,
) -> Tuple[DataLoader, DataLoader, LabelEncoder]:
    train_paths: List[Path] = []
    train_labels_raw: List[str] = []
    val_paths: List[Path] = []
    val_labels_raw: List[str] = []

    test_set = set(test_strains)
    for strain, paths in strain_segments.items():
        species = strain_to_species.get(strain)
        if not species:
            continue
        if strain in test_set:
            val_paths.extend(paths)
            val_labels_raw.extend([species] * len(paths))
        else:
            train_paths.extend(paths)
            train_labels_raw.extend([species] * len(paths))

    le = LabelEncoder()
    all_labels = train_labels_raw + val_labels_raw
    le.fit(all_labels)

    data_transforms = {
        "train": transforms.Compose([
            transforms.Resize((HEIGHT, WIDTH)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(10),
            transforms.ColorJitter(brightness=0.1, contrast=0.1),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]),
        "val": transforms.Compose([
            transforms.Resize((HEIGHT, WIDTH)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]),
    }

    train_ds = SegmentDataset(train_paths, le.transform(train_labels_raw), data_transforms["train"])
    val_ds = SegmentDataset(val_paths, le.transform(val_labels_raw), data_transforms["val"])

    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=2, pin_memory=True)
    val_dl = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=1, pin_memory=True)

    print(f"  Train: {len(train_paths)} segments, Val: {len(val_paths)} segments, Classes: {len(le.classes_)}")
    return train_dl, val_dl, le


# ── Model ──────────────────────────────────────────────────────────────────


def build_model(num_classes: int, device: torch.device) -> nn.Module:
    model = efficientnet_b1(weights=EfficientNet_B1_Weights.DEFAULT)
    for param in model.parameters():
        param.requires_grad = True
    num_ftrs = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(num_ftrs, num_classes)
    return model.to(device)


def save_backbone_weights(model: nn.Module, save_path: Path):
    state = model.state_dict()
    backbone = {k: v for k, v in state.items() if not k.startswith("classifier.")}
    torch.save(backbone, save_path)


# ── Training loop ──────────────────────────────────────────────────────────


def train_one_fold(
    model, train_dl, val_dl, criterion, optimizer, device,
    num_epochs: int, patience: int, save_path: Path,
) -> Dict[str, List[float]]:
    history = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}
    best_acc = 0.0
    best_state = copy.deepcopy(model.state_dict())
    no_improve = 0

    for epoch in range(num_epochs):
        for phase, loader in [("train", train_dl), ("val", val_dl)]:
            model.train() if phase == "train" else model.eval()
            running_loss, running_correct, total = 0.0, 0, 0

            for inputs, labels in loader:
                inputs, labels = inputs.to(device), labels.to(device)
                optimizer.zero_grad()
                with torch.set_grad_enabled(phase == "train"):
                    outputs = model(inputs)
                    loss = criterion(outputs, labels)
                    if phase == "train":
                        loss.backward()
                        optimizer.step()
                running_loss += loss.item() * inputs.size(0)
                _, preds = torch.max(outputs, 1)
                running_correct += (preds == labels).sum().item()
                total += labels.size(0)

            epoch_loss = running_loss / total
            epoch_acc = running_correct / total
            history[f"{'train' if phase == 'train' else 'val'}_loss"].append(round(epoch_loss, 6))
            history[f"{'train' if phase == 'train' else 'val'}_acc"].append(round(epoch_acc, 6))

            print(f"  Epoch {epoch+1:3d} {phase:5s} | loss={epoch_loss:.4f}  acc={epoch_acc:.4f}")

            if phase == "val":
                if epoch_acc > best_acc:
                    best_acc = epoch_acc
                    best_state = copy.deepcopy(model.state_dict())
                    no_improve = 0
                    save_backbone_weights(model, save_path)
                else:
                    no_improve += 1

        if no_improve >= patience:
            print(f"  Early stopping at epoch {epoch+1}")
            break

    model.load_state_dict(best_state)
    return history


# ── Main ───────────────────────────────────────────────────────────────────


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    folds_df = pd.read_csv(FOLDS_CSV)
    strain_segments = collect_segments()
    strain_to_species = strain_to_species_from_original_prepared()

    print(f"Strains with segments: {len(strain_segments)}")
    for strain, paths in sorted(strain_segments.items()):
        print(f"  {strain}: {len(paths)} segments -> {strain_to_species.get(strain, '???')}")

    for fold_idx in range(1, N_FOLDS + 1):
        print(f"\n{'='*60}")
        print(f"Fold {fold_idx}")
        test_strains = folds_df[folds_df["fold"] == fold_idx]["strain"].tolist()
        print(f"  Test strains: {test_strains}")

        train_dl, val_dl, le = build_dataloaders(
            strain_segments, strain_to_species, test_strains, BATCH_SIZE
        )

        model = build_model(len(le.classes_), device)
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

        save_path = WEIGHTS / f"fold{fold_idx - 1}_EfficientNetB1_finetuned.pth"
        history = train_one_fold(
            model, train_dl, val_dl, criterion, optimizer, device,
            NUM_EPOCHS, PATIENCE, save_path,
        )

        history_path = WEIGHTS / f"fold{fold_idx - 1}_EfficientNetB1_history.json"
        history_path.write_text(json.dumps(history, indent=2))

        print(f"  Fold {fold_idx} best val acc: {max(history['val_acc']):.4f}")
        print(f"  Saved: {save_path}")

    print("\nAll folds complete.")


if __name__ == "__main__":
    main()
