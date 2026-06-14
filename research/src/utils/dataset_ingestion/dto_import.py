"""
DTO Original Dataset Importer — imports Dataset/original/ into PostgreSQL + Qdrant.

Folder format:  {STRAIN} {SPECIES_NAME}
  e.g. "DTO 148-D1 Penicillium polonicum"

File format:    {STRAIN} {MEDIA}{angle}_edited.jpg
  e.g. "DTO 148-D1 CYAob_edited.jpg" → media=CYA, angle=ob

Pipeline:
  1. Scan folders → extract species, strain
  2. Scan files → extract media, angle
  3. Register species/media/strains via backend API
  4. Upload each image + segment via backend API
  5. Trigger Qdrant reindex
  6. Log progress with structured output
"""

from __future__ import annotations

import logging
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, stream=sys.stderr)
logger = logging.getLogger("dto-import")


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
    r"(CREA|CYA30|CYAS|CYA|DG18|MEA|YES|OA|M40Y)(ob|rev)",
    re.IGNORECASE,
)


def scan_dto_dataset(root: str | Path) -> DtoManifest:
    """Walk Dataset/original/ and extract all metadata from folder + filenames."""
    root = Path(root)
    manifest = DtoManifest()

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
                # Normalize CYA30 and CYAS to CYA
                if raw_media in ("CYA30", "CYAS"):
                    media = "CYA"
                else:
                    media = raw_media
                angle = m2.group(2).lower()
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

    logger.info(
        "Scanned %d species, %d media, %d images from %s",
        len(manifest.species),
        len(manifest.media),
        len(manifest.images),
        root,
    )
    return manifest


# ---------------------------------------------------------------------------
# Backend API Client
# ---------------------------------------------------------------------------
class BackendClient:
    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self._token: str | None = None

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

    def _check(self, resp: requests.Response, ctx: str) -> dict[str, Any]:
        if resp.status_code in (200, 201, 202):
            return resp.json()
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text[:200]
        raise RuntimeError(f"{ctx} ({resp.status_code}): {detail}")

    def ensure_species(self, name: str) -> dict:
        items = self._check(self.session.get(f"{self.base_url}/species?limit=200"), "list species")
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
        items = self._check(self.session.get(f"{self.base_url}/media?limit=200"), "list media")
        for m in items.get("items", []):
            if m["name"].lower() == name.lower():
                return m
        return self._check(
            self.session.post(f"{self.base_url}/media", json={"name": name}),
            f"create media '{name}'",
        )

    def upload_image(self, source_path: Path, strain: str, media: str, species: str) -> dict:
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
# Importer
# ---------------------------------------------------------------------------
class DtoImporter:
    def __init__(self, client: BackendClient, manifest: DtoManifest):
        self.client = client
        self.manifest = manifest
        self.stats = ImportStats()

    def run(self) -> ImportStats:
        self.stats.start_time = time.time()

        # Step 1: Register species
        logger.info("=== Step 1: Registering %d species ===", len(self.manifest.species))
        species_map: dict[str, dict] = {}
        for name in sorted(self.manifest.species):
            try:
                species_map[name] = self.client.ensure_species(name)
                self.stats.species_created += 1
                logger.info("  species: %s", name)
            except Exception as e:
                self.stats.errors.append(f"species '{name}': {e}")
                logger.error("  FAIL species '%s': %s", name, e)

        # Step 2: Register media
        logger.info("=== Step 2: Registering %d media ===", len(self.manifest.media))
        media_map: dict[str, dict] = {}
        for name in sorted(self.manifest.media):
            try:
                media_map[name] = self.client.ensure_media(name)
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
    import argparse

    parser = argparse.ArgumentParser(description="Import DTO original dataset into backend")
    parser.add_argument(
        "--source", default="/home/dat/dev/mycoai_projects/Dataset/original",
        help="Path to Dataset/original/"
    )
    parser.add_argument(
        "--api-url", default="http://localhost:8000/api/v1",
        help="Backend API base URL"
    )
    parser.add_argument(
        "--email", default="owner@test.dev",
        help="Data owner email"
    )
    parser.add_argument(
        "--password", default="password123",
        help="Data owner password"
    )
    parser.add_argument(
        "--scan-only", action="store_true",
        help="Only scan and print manifest, don't import"
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Limit number of images to import (0 = all)"
    )
    args = parser.parse_args()

    manifest = scan_dto_dataset(args.source)
    logger.info("Species: %s", sorted(manifest.species))
    logger.info("Media: %s", sorted(manifest.media))
    logger.info("Images: %d", len(manifest.images))

    if args.scan_only:
        logger.info("Scan-only mode. Bye!")
        return

    if args.limit > 0:
        manifest.images = manifest.images[: args.limit]
        logger.info("Limited to %d images", args.limit)

    client = BackendClient(base_url=args.api_url)
    client.login(args.email, args.password)

    # Show current state
    try:
        stats_before = client.dashboard_stats()
        logger.info("Before: %s", stats_before)
    except Exception:
        pass

    importer = DtoImporter(client, manifest)
    stats = importer.run()

    # Show final state
    try:
        stats_after = client.dashboard_stats()
        logger.info("After: %s", stats_after)
    except Exception:
        pass

    if stats.errors:
        logger.warning("%d errors occurred during import", len(stats.errors))
        sys.exit(1)


if __name__ == "__main__":
    main()
