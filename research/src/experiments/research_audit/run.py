from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from qdrant_client.http.exceptions import UnexpectedResponse

from src.config import (
    DATASET_ROOT,
    PREPARED_ITEMS_METADATA_PATH,
    PREPARED_SEGMENTS_METADATA_PATH,
    PROJECT_ROOT,
    QDRANT_API_KEY,
    QDRANT_URL,
    RESULTS_DIR,
    STRAIN_SPECIES_MAPPING_PATH,
    WEIGHTS_DIR,
)

MONOREPO_ROOT = PROJECT_ROOT.parent
MONOREPO_DATASET_ROOT = MONOREPO_ROOT / "Dataset"
MONOREPO_RESULTS_DIR = MONOREPO_ROOT / "results"
MONOREPO_WEIGHTS_DIR = MONOREPO_ROOT / "weights"
AUDIT_DIR = RESULTS_DIR / "research_audit"


def _safe_count_dir(path: Path) -> int:
    if not path.exists() or not path.is_dir():
        return 0
    return sum(1 for _ in path.iterdir())


def _summarize_dataset() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    roots = [
        ("effective", DATASET_ROOT),
        ("monorepo", MONOREPO_DATASET_ROOT),
    ]
    for scope, root in roots:
        if not root.exists():
            rows.append(
                {
                    "scope": scope,
                    "root": str(root),
                    "name": "<missing>",
                    "type": "missing",
                    "exists": False,
                    "child_count": None,
                    "size_bytes": None,
                }
            )
            continue
        for name in sorted(root.iterdir(), key=lambda p: p.name):
            rows.append(
                {
                    "scope": scope,
                    "root": str(root),
                    "name": name.name,
                    "type": "dir" if name.is_dir() else "file",
                    "exists": True,
                    "child_count": _safe_count_dir(name) if name.is_dir() else None,
                    "size_bytes": None if name.is_dir() else name.stat().st_size,
                }
            )
    return pd.DataFrame(rows)


def _load_json_count(path: Path) -> int | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return len(data)
    return None


def _summarize_reports() -> dict[str, Any]:
    report_root = Path(__file__).resolve().parents[3] / "report"
    docs_root = Path(__file__).resolve().parents[4] / "docs"
    report_dirs = sorted([p.name for p in report_root.iterdir() if p.is_dir()]) if report_root.exists() else []
    graduation_files = sorted([p.name for p in (docs_root / "graduation_report" / "content").iterdir()]) if (docs_root / "graduation_report" / "content").exists() else []
    return {
        "report_root": str(report_root),
        "report_dirs": report_dirs,
        "graduation_content_files": graduation_files,
    }


def _query_qdrant() -> dict[str, Any]:
    from qdrant_client import QdrantClient

    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=30)
    collections = client.get_collections().collections
    payload: list[dict[str, Any]] = []
    for collection in collections:
        item: dict[str, Any] = {"name": collection.name}
        try:
            info = client.get_collection(collection.name)
            item["points_count"] = getattr(info, "points_count", None)
            item["vectors_count"] = getattr(info, "vectors_count", None)
        except UnexpectedResponse as exc:
            item["error"] = str(exc)
        payload.append(item)
    return {
        "url": QDRANT_URL,
        "collections": payload,
    }


def _mapping_summary(path: Path) -> tuple[int | None, int | None]:
    if not path.exists():
        return None, None
    mapping_df = pd.read_csv(path)
    rows = len(mapping_df)
    species_count = mapping_df["Species"].nunique() if "Species" in mapping_df else None
    return rows, species_count


def _build_inventory() -> dict[str, Any]:
    effective_mapping_rows, effective_species_count = _mapping_summary(STRAIN_SPECIES_MAPPING_PATH)
    monorepo_mapping_rows, monorepo_species_count = _mapping_summary(MONOREPO_DATASET_ROOT / "strain_to_specy.csv")

    effective_weight_files = sorted([p.name for p in WEIGHTS_DIR.iterdir()]) if WEIGHTS_DIR.exists() else []
    monorepo_weight_files = sorted([p.name for p in MONOREPO_WEIGHTS_DIR.iterdir()]) if MONOREPO_WEIGHTS_DIR.exists() else []

    return {
        "effective": {
            "dataset_root": str(DATASET_ROOT),
            "weights_dir": str(WEIGHTS_DIR),
            "results_dir": str(RESULTS_DIR),
            "prepared_items_count": _load_json_count(PREPARED_ITEMS_METADATA_PATH),
            "prepared_segments_count": _load_json_count(PREPARED_SEGMENTS_METADATA_PATH),
            "strain_mapping_rows": effective_mapping_rows,
            "species_count": effective_species_count,
            "weight_files": effective_weight_files,
            "results_exists": RESULTS_DIR.exists(),
        },
        "monorepo": {
            "dataset_root": str(MONOREPO_DATASET_ROOT),
            "weights_dir": str(MONOREPO_WEIGHTS_DIR),
            "results_dir": str(MONOREPO_RESULTS_DIR),
            "prepared_items_count": _load_json_count(MONOREPO_DATASET_ROOT / "prepared_items_metadata.json"),
            "prepared_segments_count": _load_json_count(MONOREPO_DATASET_ROOT / "prepared_segments_metadata.json"),
            "strain_mapping_rows": monorepo_mapping_rows,
            "species_count": monorepo_species_count,
            "weight_files": monorepo_weight_files,
            "results_exists": MONOREPO_RESULTS_DIR.exists(),
        },
    }


def _build_risk_flags(inventory: dict[str, Any], qdrant_state: dict[str, Any]) -> str:
    risks: list[str] = []
    effective = inventory["effective"]
    monorepo = inventory["monorepo"]
    risks.append("- Historical metrics are untrusted until rerun under fresh-query leakage-safe protocol.")
    risks.append("- Fine-tune training currently depends on a global Test column and needs fold-safe manifests.")
    risks.append("- Retrieval benchmark code must be forced through fresh image query path with held-out strain exclusion.")
    if effective["dataset_root"] != monorepo["dataset_root"]:
        risks.append("- Config drift: research runtime resolves local research/ Dataset, results, and weights instead of monorepo shared paths.")
    if not monorepo.get("weight_files"):
        risks.append("- No weights found in monorepo weights/; finetuned benchmark cannot be reproduced without retraining or restoring weights.")
    if monorepo.get("prepared_segments_count") in (None, 0):
        risks.append("- Monorepo prepared segment metadata missing or empty.")
    if len(qdrant_state.get("collections", [])) == 0:
        risks.append("- No Qdrant collections visible from configured endpoint.")
    return "# Risk Flags\n\n" + "\n".join(risks) + "\n"


def main() -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    dataset_summary = _summarize_dataset()
    dataset_summary.to_csv(AUDIT_DIR / "dataset_summary.csv", index=False)

    inventory = _build_inventory()
    (AUDIT_DIR / "inventory.json").write_text(json.dumps(inventory, indent=2))

    try:
        qdrant_state = _query_qdrant()
    except Exception as exc:
        qdrant_state = {"url": QDRANT_URL, "collections": [], "error": str(exc)}
    (AUDIT_DIR / "qdrant_collections.json").write_text(json.dumps(qdrant_state, indent=2))

    reports_summary = _summarize_reports()
    (AUDIT_DIR / "reports_summary.json").write_text(json.dumps(reports_summary, indent=2))

    risk_flags = _build_risk_flags(inventory, qdrant_state)
    (AUDIT_DIR / "risk_flags.md").write_text(risk_flags)

    print(json.dumps({
        "audit_dir": str(AUDIT_DIR),
        "files": [
            "inventory.json",
            "dataset_summary.csv",
            "qdrant_collections.json",
            "reports_summary.json",
            "risk_flags.md",
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
