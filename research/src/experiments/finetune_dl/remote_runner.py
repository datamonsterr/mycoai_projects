#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, Sequence

PYTHON_BIN = os.getenv("MYCOAI_REMOTE_PYTHON", sys.executable)

PROJECT = Path("/workspace")
WEIGHTS_ROOT = PROJECT / "weights"
RESULTS_ROOT = PROJECT / "results"

MODELS = ["ResNet50", "MobileNetV2", "EfficientNetB1"]
SEGMENT_METHODS = ["yolo", "kmeans"]


def run(cmd: Sequence[str], env: Optional[Dict[str, str]] = None) -> str:
    full_env = {**os.environ, **(env or {})}
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=PROJECT, env=full_env
    )
    if result.returncode != 0:
        print(f"FAIL: {cmd}\n{result.stderr}", file=sys.stderr)
        return ""
    return result.stdout


def clear_old_weights() -> None:
    for method in SEGMENT_METHODS:
        root = WEIGHTS_ROOT / f"{method}_finetuned"
        if root.exists():
            shutil.rmtree(root)


def train_all() -> Dict[str, dict]:
    summaries: Dict[str, dict] = {}
    clear_old_weights()
    for method in SEGMENT_METHODS:
        for model in MODELS:
            key = f"{method}/{model}"
            print(f"Training {key} ...")
            cmd = [
                PYTHON_BIN,
                "-m",
                "src.experiments.finetune_dl.train_strain_holdout",
                "--model-name",
                model,
                "--segment-method",
                method,
                "--epochs",
                "12",
                "--batch-size",
                "16",
            ]
            if model == MODELS[0]:
                cmd.append("--clear-existing")
            out = run(cmd)
            if out:
                summaries[key] = json.loads(out)
            print(
                f"  best_val_acc={summaries.get(key, {}).get('best_val_accuracy', 'N/A')}"
            )
    return summaries


def extract_features(method: str, output_path: Path) -> None:
    print(f"Extracting features for {method} ...")
    run(
        [
            PYTHON_BIN,
            "-c",
            f"from src.experiments.feature_extraction.generate_features import generate_features; "
            f"generate_features(output_path='{output_path}', segment_method='{method}')",
        ],
        env={"MYCOAI_FINETUNED_SEGMENT_METHOD": method},
    )


def feature_extraction_all() -> None:
    for method in SEGMENT_METHODS:
        output_path = RESULTS_ROOT / f"features_{method}.json"
        extract_features(method, output_path)


def benchmark_retrieval() -> Dict[str, dict]:
    results: Dict[str, dict] = {}
    for method in SEGMENT_METHODS:
        env = {"MYCOAI_FINETUNED_SEGMENT_METHOD": method}
        extractors = [
            "efficientnetb1_finetuned",
            "resnet50_finetuned",
            "mobilenetv2_finetuned",
            "efficientnetb1",
            "resnet50",
            "mobilenetv2",
            "hog",
            "gabor",
            "colorhistogram",
            "colorhistogramhs",
        ]
        base = RESULTS_ROOT / f"retrieval_k7_{method}"
        for strategy in ["weighted", "freq_strength"]:
            key = f"{method}/{strategy}"
            print(f"Benchmarking {key} ...")
            run(
                [
                    PYTHON_BIN,
                    "-m",
                    "src.experiments.retrieval.run",
                    "comprehensive",
                    "--identifier",
                    str(base),
                    "--extractors",
                    *extractors,
                    "--env_strategies",
                    "E1",
                    "E2",
                    "--agg_strategies",
                    strategy,
                    "--k",
                    "7",
                    "--max_visualizations",
                    "0",
                ],
                env=env,
            )
            # Scan for per-extractor CSV files
            accuracies: Dict[str, float] = {}
            for csv_path in sorted(base.glob(f"*_{strategy}_E1/evaluation.csv")):
                try:
                    import pandas as pd

                    df = pd.read_csv(csv_path)
                    if not df.empty and "correct" in df.columns:
                        acc = df["correct"].mean()
                        accuracies[csv_path.parent.name] = acc
                except Exception:
                    continue
            results[key] = {
                "best_accuracy": max(accuracies.values()) if accuracies else 0.0,
                "accuracies": accuracies,
            }
    return results


def collect_artifacts(run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        WEIGHTS_ROOT,
        run_dir / "weights",
        dirs_exist_ok=True,
        symlinks=False,
        ignore=shutil.ignore_patterns("segmentation"),
    )
    for pattern in ["retrieval_k7_*", "*_finetuned"]:
        for p in RESULTS_ROOT.glob(pattern):
            target = run_dir / p.relative_to(RESULTS_ROOT)
            if p.is_dir():
                shutil.copytree(p, target, dirs_exist_ok=True, symlinks=False)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, target)
    manifest = {
        "features_yolo": str(RESULTS_ROOT / "features_yolo.json"),
        "features_kmeans": str(RESULTS_ROOT / "features_kmeans.json"),
    }
    (run_dir / "feature_manifest.json").write_text(json.dumps(manifest, indent=2))


def main() -> None:
    if len(sys.argv) < 2:
        print(
            f"Usage: {sys.argv[0]} <train|extract|benchmark|all> [run-dir]",
            file=sys.stderr,
        )
        sys.exit(1)
    command = sys.argv[1]
    run_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else RESULTS_ROOT / "remote_run"

    if command == "train":
        clear_old_weights()
        summaries = train_all()
        (run_dir / "train_summaries.json").write_text(json.dumps(summaries, indent=2))
        collect_artifacts(run_dir)
    elif command == "extract":
        feature_extraction_all()
        collect_artifacts(run_dir)
    elif command == "benchmark":
        bench = benchmark_retrieval()
        (run_dir / "benchmark_summaries.json").write_text(json.dumps(bench, indent=2))
        collect_artifacts(run_dir)
    elif command == "all":
        clear_old_weights()
        summaries = train_all()
        (run_dir / "train_summaries.json").write_text(json.dumps(summaries, indent=2))
        feature_extraction_all()
        bench = benchmark_retrieval()
        (run_dir / "benchmark_summaries.json").write_text(json.dumps(bench, indent=2))
        collect_artifacts(run_dir)
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
