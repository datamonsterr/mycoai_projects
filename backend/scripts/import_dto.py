#!/usr/bin/env python3
"""
DTO Original Dataset Import Script — imports Dataset/original/ into the backend.

Pipeline:
  1. Scan Dataset/original/ folders → extract species, strain, media, angle
  2. Connect to backend API (or DB directly if --direct-db flag)
  3. Register species → media → strains
  4. Upload + segment each image
  5. Trigger Qdrant reindex for all new segments
  6. Log progress at every step with structured output

Folder format:  {STRAIN} {SPECIES_NAME}
  e.g. "DTO 148-D1 Penicillium polonicum"

File format:    {STRAIN} {MEDIA}{angle}_edited.jpg
  e.g. "DTO 148-D1 CYAob_edited.jpg" → media=CYA, angle=ob

Usage:
  # Scan dataset only (no import)
  python scripts/import_dto.py --scan-only

  # Import via backend API (requires backend running)
  python scripts/import_dto.py --api-url http://localhost:8000/api/v1

  # Import directly to DB (no API needed)
  python scripts/import_dto.py --direct-db --source Dataset/original

  # Import first 10 images for testing
  python scripts/import_dto.py --limit 10
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logger = logging.getLogger("dto-import")


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
@dataclass
class DtoImage:
    source_path: Path
    strain_code: str
    species_name: str
    media_name: str
    angle: str
    original_filename: str


@dataclass
class DtoManifest:
    species: set[str] = field(default_factory=set)
    media: set[str] = field(default_factory=set)
    images: list[DtoImage] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"Manifest: {len(self.species)} species, "
            f"{len(self.media)} media, "
            f"{len(self.images)} images"
        )


@dataclass
class ImportStats:
    species_created: int = 0
    media_created: int = 0
    strains_created: int = 0
    images_uploaded: int = 0
    images_failed: int = 0
    segments: int = 0
    qdrant_indexed: int = 0
    errors: list[str] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0

    def elapsed(self) -> float:
        return self.end_time - self.start_time

    def summary(self) -> str:
        lines = [
            f"Species:  {self.species_created}",
            f"Media:    {self.media_created}",
            f"Strains:  {self.strains_created}",
            f"Images:   {self.images_uploaded} uploaded, {self.images_failed} failed",
            f"Segments: {self.segments}",
            f"Qdrant:   {self.qdrant_indexed} indexed",
            f"Duration: {self.elapsed():.1f}s",
        ]
        if self.errors:
            lines.append(f"Errors:   {len(self.errors)}")
            for e in self.errors[:5]:
                lines.append(f"  - {e}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
DTO_FOLDER_RE = re.compile(r"^(DTO\s+[\d\-A-Za-z]+)\s+(Penicillium\s+\w+.*)$")
MEDIA_ANGLE_RE = re.compile(
    r"(CREA|CYA30|CYAS|CYA|DG18|MEA|YES|OA|M40Y)(ob|rev|o|r)",
    re.IGNORECASE,
)


def scan_dto_dataset(root: str | Path) -> DtoManifest:
    """Walk Dataset/original/ and extract all metadata from folder + filenames."""
    root = Path(root)
    manifest = DtoManifest()

    logger.info("Scanning dataset root: %s", root)

    for folder in sorted(root.iterdir()):
        if not folder.is_dir():
            continue
        folder_name = folder.name

        m = DTO_FOLDER_RE.match(folder_name)
        if not m:
            logger.warning("Skipping unrecognized folder: %s", folder_name)
            continue

        strain_code = m.group(1).strip()
        species_name = m.group(2).strip()
        manifest.species.add(species_name)
        logger.debug("Folder: strain=%s species=%s", strain_code, species_name)

        for fpath in sorted(folder.iterdir()):
            if not fpath.is_file():
                continue
            if fpath.suffix.lower() not in {".jpg", ".jpeg", ".png", ".jpe"}:
                continue
            if fpath.name.lower() in {"thumbs.db", ".ds_store", "desktop.ini"}:
                continue

            media = "unknown"
            angle = "unknown"
            m2 = MEDIA_ANGLE_RE.search(fpath.stem)
            if m2:
                raw_media = m2.group(1).upper()
                media = "CYA" if raw_media in ("CYA30", "CYAS") else raw_media
                raw = m2.group(2).lower()
                angle = {"o": "ob", "r": "rev"}.get(raw, raw)
                if media != "unknown":
                    manifest.media.add(media)

            manifest.images.append(
                DtoImage(
                    source_path=fpath,
                    strain_code=strain_code,
                    species_name=species_name,
                    media_name=media,
                    angle=angle,
                    original_filename=fpath.name,
                )
            )

    logger.info("Scan complete: %s", manifest.summary())
    return manifest


# ---------------------------------------------------------------------------
# Backend API Client
# ---------------------------------------------------------------------------
class BackendClient:
    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        self.base_url = base_url.rstrip("/")
        self.session = self._create_session()
        self._token: str | None = None

    @staticmethod
    def _create_session():
        import requests
        return requests.Session()

    def login(self, email: str, password: str) -> str:
        resp = self.session.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password},
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        self.session.headers["Authorization"] = f"Bearer {self._token}"
        logger.info("Logged in as %s", email)
        return self._token

    def _check(self, resp, ctx: str) -> dict[str, Any]:
        if resp.status_code in (200, 201, 202):
            return resp.json()
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text[:200]
        raise RuntimeError(f"{ctx} ({resp.status_code}): {detail}")

    def ensure_species(self, name: str) -> dict:
        items = self._check(
            self.session.get(f"{self.base_url}/species?limit=200"), "list species"
        )
        for s in items.get("items", []):
            if s["name"].lower() == name.lower():
                return s
        return self._check(
            self.session.post(f"{self.base_url}/species", json={"name": name}),
            f"create species '{name}'",
        )

    def ensure_media(self, name: str) -> dict:
        if name.lower() == "unknown":
            return {"id": "00000000-0000-0000-0000-000000000000", "name": "unknown"}
        items = self._check(
            self.session.get(f"{self.base_url}/media?limit=200"), "list media"
        )
        for m in items.get("items", []):
            if m["name"].lower() == name.lower():
                return m
        return self._check(
            self.session.post(f"{self.base_url}/media", json={"name": name}),
            f"create media '{name}'",
        )

    def upload_image(
        self, source_path: Path, strain: str, media: str, species: str
    ) -> dict:
        with open(source_path, "rb") as f:
            resp = self.session.post(
                f"{self.base_url}/images",
                files={"image": (source_path.name, f, "image/jpeg")},
                data={"strain": strain, "media": media, "species": species},
            )
        return self._check(resp, f"upload {source_path.name}")

    def trigger_reindex(self) -> dict:
        return self._check(
            self.session.post(
                f"{self.base_url}/index/reindex",
                json={"scope": "full_active"},
            ),
            "reindex",
        )

    def dashboard_stats(self) -> dict:
        return self._check(
            self.session.get(f"{self.base_url}/dashboard/stats"),
            "dashboard",
        )


# ---------------------------------------------------------------------------
# Direct DB Importer (uses SQLAlchemy async session directly)
# ---------------------------------------------------------------------------
class DirectDbImporter:
    def __init__(self, source_dir: str, manifest: DtoManifest, method: str = "kmeans"):
        self.source_dir = source_dir
        self.manifest = manifest
        self.method = method
        self.stats = ImportStats()

    def run(self) -> ImportStats:
        import asyncio

        return asyncio.run(self._run_async())

    async def _run_async(self) -> ImportStats:
        from mycoai_retrieval_backend.config import get_settings
        from mycoai_retrieval_backend.database import async_session as _session_factory
        from mycoai_retrieval_backend.segmentation import SegmentationPipeline
        from mycoai_retrieval_backend.tasks.batch import run as batch_run

        self.stats.start_time = time.time()
        settings = get_settings()
        pipeline = SegmentationPipeline(settings.upload_root)

        async with _session_factory() as db:
            result = await batch_run(
                source_dir=self.source_dir,
                db=db,
                pipeline=pipeline,
                method=self.method,
                limit=0,
            )

            self.stats.images_uploaded = result.get("successful", 0)
            self.stats.images_failed = result.get("failed", 0)
            self.stats.segments = result.get("segments", 0)
            self.stats.qdrant_indexed = result.get("qdrant_indexed", 0)
            errors = result.get("errors", [])
            self.stats.errors = [str(e) for e in errors]

        self.stats.end_time = time.time()
        return self.stats


# ---------------------------------------------------------------------------
# API-based Importer
# ---------------------------------------------------------------------------
class ApiImporter:
    def __init__(self, client: BackendClient, manifest: DtoManifest):
        self.client = client
        self.manifest = manifest
        self.stats = ImportStats()

    def run(self) -> ImportStats:
        self.stats.start_time = time.time()

        # Step 1: Register species
        logger.info("=== Step 1: Registering %d species ===", len(self.manifest.species))
        for name in sorted(self.manifest.species):
            try:
                self.client.ensure_species(name)
                self.stats.species_created += 1
                logger.info("  species: %s", name)
            except Exception as e:
                self.stats.errors.append(f"species '{name}': {e}")
                logger.error("  FAIL species '%s': %s", name, e)

        # Step 2: Register media
        logger.info("=== Step 2: Registering %d media ===", len(self.manifest.media))
        for name in sorted(self.manifest.media):
            try:
                self.client.ensure_media(name)
                self.stats.media_created += 1
                logger.info("  media: %s", name)
            except Exception as e:
                self.stats.errors.append(f"media '{name}': {e}")
                logger.error("  FAIL media '%s': %s", name, e)

        # Step 3: Upload images (auto-creates strains)
        logger.info("=== Step 3: Uploading %d images ===", len(self.manifest.images))
        total_segments = 0
        batch_start = time.time()
        for i, img in enumerate(self.manifest.images):
            try:
                result = self.client.upload_image(
                    source_path=img.source_path,
                    strain=img.strain_code,
                    media=img.media_name,
                    species=img.species_name,
                )
                self.stats.images_uploaded += 1
                seg_count = len(result.get("segments", []))
                total_segments += seg_count
                self.stats.segments += seg_count

                if (i + 1) % 20 == 0:
                    elapsed = time.time() - batch_start
                    rate = (i + 1) / elapsed if elapsed > 0 else 0
                    logger.info(
                        "  progress: %d/%d images (%.1f img/s, %d segments)",
                        i + 1, len(self.manifest.images), rate, total_segments,
                    )
            except Exception as e:
                self.stats.images_failed += 1
                self.stats.errors.append(f"image '{img.source_path.name}': {e}")
                logger.error("  FAIL '%s': %s", img.source_path.name, str(e)[:100])

        # Step 4: Trigger Qdrant reindex
        logger.info("=== Step 4: Triggering Qdrant reindex ===")
        try:
            reindex_result = self.client.trigger_reindex()
            self.stats.qdrant_indexed = reindex_result.get("indexed", 0)
            logger.info("  Qdrant: %d points indexed", self.stats.qdrant_indexed)
        except Exception as e:
            self.stats.errors.append(f"reindex: {e}")
            logger.error("  FAIL reindex: %s", e)

        self.stats.end_time = time.time()
        logger.info("=== Import Complete ===\n%s", self.stats.summary())
        return self.stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import DTO original dataset into MycoAI backend (PostgreSQL + Qdrant)"
    )
    parser.add_argument(
        "--source",
        default="/home/dat/dev/mycoai_projects/Dataset/original",
        help="Path to Dataset/original/ directory",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000/api/v1",
        help="Backend API base URL (for API import mode)",
    )
    parser.add_argument(
        "--email",
        default="owner@mycoai.dev",
        help="Data owner email for API auth",
    )
    parser.add_argument(
        "--password",
        default="password123",
        help="Data owner password for API auth",
    )
    parser.add_argument(
        "--scan-only",
        action="store_true",
        help="Only scan and print manifest, do not import",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of images to import (0 = all)",
    )
    parser.add_argument(
        "--direct-db",
        action="store_true",
        help="Import directly to database (no API needed, requires DB config)",
    )
    parser.add_argument(
        "--method",
        default="kmeans",
        choices=["kmeans", "contour"],
        help="Segmentation method",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    setup_logging(verbose=args.verbose)

    # Step 1: Scan dataset
    logger.info("========================================")
    logger.info("DTO Dataset Import - Step 1: Scanning")
    logger.info("========================================")
    manifest = scan_dto_dataset(args.source)

    logger.info("Species: %s", sorted(manifest.species))
    logger.info("Media: %s", sorted(manifest.media))
    logger.info("Images: %d", len(manifest.images))

    if args.scan_only:
        logger.info("Scan-only mode. Exporting manifest...")
        for img in manifest.images[:20]:
            logger.info(
                "  %s → species=%s strain=%s media=%s angle=%s",
                img.original_filename,
                img.species_name,
                img.strain_code,
                img.media_name,
                img.angle,
            )
        if len(manifest.images) > 20:
            logger.info("  ... and %d more images", len(manifest.images) - 20)
        return

    if args.limit > 0:
        manifest.images = manifest.images[: args.limit]
        logger.info("Limited to %d images", args.limit)

    # Step 2-4: Import
    if args.direct_db:
        logger.info("========================================")
        logger.info("DTO Dataset Import - Steps 2-4: Direct DB Import")
        logger.info("========================================")
        importer = DirectDbImporter(args.source, manifest, method=args.method)
        stats = importer.run()
    else:
        logger.info("========================================")
        logger.info("DTO Dataset Import - Steps 2-4: API Import")
        logger.info("========================================")
        client = BackendClient(base_url=args.api_url)
        client.login(args.email, args.password)

        try:
            before = client.dashboard_stats()
            logger.info("Before import: %s", before)
        except Exception:
            pass

        importer = ApiImporter(client, manifest)
        stats = importer.run()

        try:
            after = client.dashboard_stats()
            logger.info("After import: %s", after)
        except Exception:
            pass

    if stats.errors:
        logger.warning("%d errors occurred during import", len(stats.errors))
        sys.exit(1)

    logger.info("Import successful!")


if __name__ == "__main__":
    main()
