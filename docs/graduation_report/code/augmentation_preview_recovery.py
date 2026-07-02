from __future__ import annotations

import random
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from torchvision import transforms

from src.config import ORIGINAL_PREPARED_DATASET_DIR

LATEX_DIR = Path("/home/dat/dev/mycoai/graduation_report/figures")
REPORT_DIR = Path("/home/dat/dev/mycoai/graduation_report/report/figures")
for directory in (LATEX_DIR, REPORT_DIR):
    directory.mkdir(parents=True, exist_ok=True)

STYLE = {
    "font.family": "serif",
    "font.size": 8,
    "axes.titlesize": 9,
    "axes.labelsize": 8,
}
plt.rcParams.update(STYLE)


def save(name: str, fig: plt.Figure) -> None:
    for directory in (LATEX_DIR, REPORT_DIR):
        fig.savefig(directory / name, dpi=200, bbox_inches="tight")
    plt.close(fig)


def load_sample_image() -> Image.Image:
    candidates = sorted(ORIGINAL_PREPARED_DATASET_DIR.glob("*/*/*/*/segments_yolo/segment_*.jpg"))
    if not candidates:
        raise FileNotFoundError("No YOLO segment images found in Dataset/original_prepared")
    random.seed(42)
    return Image.open(random.choice(candidates)).convert("RGB")


def pil_to_array(image: Image.Image) -> np.ndarray:
    return np.asarray(image)


def main() -> None:
    original = load_sample_image()
    resize = transforms.Resize((224, 224))
    base = resize(original)

    views = [
        ("Original", base),
        (
            "Random cut",
            transforms.RandomResizedCrop((224, 224), scale=(0.75, 0.82), ratio=(0.95, 1.05))(original),
        ),
        (
            "Brightness +",
            transforms.ColorJitter(brightness=(1.18, 1.18), contrast=(1.0, 1.0))(base),
        ),
        (
            "Contrast +",
            transforms.ColorJitter(brightness=(1.0, 1.0), contrast=(1.22, 1.22))(base),
        ),
        (
            "Rotate + cut",
            transforms.Compose([
                transforms.RandomRotation((8, 8)),
                transforms.RandomResizedCrop((224, 224), scale=(0.78, 0.9), ratio=(0.95, 1.05)),
            ])(original),
        ),
        (
            "Combined",
            transforms.Compose([
                transforms.RandomResizedCrop((224, 224), scale=(0.75, 0.9), ratio=(0.9, 1.1)),
                transforms.ColorJitter(brightness=(0.82, 1.18), contrast=(0.82, 1.22)),
                transforms.RandomHorizontalFlip(p=1.0),
            ])(original),
        ),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(7.2, 4.8))
    for ax, (title, image) in zip(axes.flat, views):
        ax.imshow(pil_to_array(image))
        ax.set_title(title)
        ax.axis("off")
    fig.suptitle("Fine-tuning augmentation policy preview", fontsize=9)
    fig.tight_layout()
    save("finetune_augmentation_preview.png", fig)
    print("Saved finetune_augmentation_preview.png")


if __name__ == "__main__":
    main()
