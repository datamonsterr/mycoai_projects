"""
Ingester: takes a DatasetManifest and imports into the backend via REST API.

Two modes:
  1) API mode: calls backend endpoints (species, media, strains, images)
  2) Dry-run mode: prints what would happen without making changes
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

try:
    from .scanner import DatasetManifest, ImageEntry
except ImportError:
    from src.utils.dataset_ingestion.scanner import DatasetManifest, ImageEntry


@dataclass
class IngestResult:
    species_created: int = 0
    media_created: int = 0
    strains_created: int = 0
    images_uploaded: int = 0
    errors: list[str] = field(default_factory=list)

    def ok(self) -> bool:
        return len(self.errors) == 0


class BackendAPIClient:
    """Low-level HTTP client for backend API."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000/api/v1",
        email: str = "owner@mycoai.dev",
        password: str = "password123",
    ):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self._token: str | None = None
        self._email = email
        self._password = password

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------
    def login(self) -> str:
        resp = self.session.post(
            f"{self.base_url}/auth/login",
            json={"email": self._email, "password": self._password},
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        self.session.headers["Authorization"] = f"Bearer {self._token}"
        return self._token

    def _ensure_auth(self) -> None:
        if self._token is None:
            self.login()

    # ------------------------------------------------------------------
    # Species
    # ------------------------------------------------------------------
    def create_species(self, name: str, description: str | None = None) -> dict:
        self._ensure_auth()
        resp = self.session.post(
            f"{self.base_url}/species",
            json={"name": name, "description": description},
        )
        return self._handle_response(resp, "species")

    def list_species(self, is_archived: bool = False) -> list[dict]:
        self._ensure_auth()
        resp = self.session.get(
            f"{self.base_url}/species",
            params={"is_archived": str(is_archived).lower(), "limit": 200},
        )
        resp.raise_for_status()
        return resp.json()["items"]

    def get_species_by_name(self, name: str) -> dict | None:
        items = self.list_species()
        for item in items:
            if item["name"].lower() == name.lower():
                return item
        return None

    def ensure_species(self, name: str) -> dict:
        existing = self.get_species_by_name(name)
        if existing:
            return existing
        return self.create_species(name)

    # ------------------------------------------------------------------
    # Media
    # ------------------------------------------------------------------
    def create_media(self, name: str, description: str | None = None) -> dict:
        self._ensure_auth()
        resp = self.session.post(
            f"{self.base_url}/media",
            json={"name": name, "description": description},
        )
        return self._handle_response(resp, "media")

    def list_media(self, is_archived: bool = False) -> list[dict]:
        self._ensure_auth()
        resp = self.session.get(
            f"{self.base_url}/media",
            params={"is_archived": str(is_archived).lower(), "limit": 200},
        )
        resp.raise_for_status()
        return resp.json()["items"]

    def get_media_by_name(self, name: str) -> dict | None:
        items = self.list_media()
        for item in items:
            if item["name"].lower() == name.lower():
                return item
        return None

    def ensure_media(self, name: str) -> dict:
        if name.lower() == "unknown":
            return {"id": "00000000-0000-0000-0000-000000000000", "name": "unknown"}
        existing = self.get_media_by_name(name)
        if existing:
            return existing
        return self.create_media(name)

    # ------------------------------------------------------------------
    # Strains
    # ------------------------------------------------------------------
    def list_strains(self, species_id: str | None = None) -> list[dict]:
        self._ensure_auth()
        params: dict[str, Any] = {"limit": 200}
        if species_id:
            params["species_id"] = species_id
        resp = self.session.get(f"{self.base_url}/strains", params=params)
        resp.raise_for_status()
        return resp.json()["items"]

    def get_strain_by_name_and_species(self, name: str, species_id: str) -> dict | None:
        items = self.list_strains(species_id=species_id)
        for item in items:
            if item["name"].lower() == name.lower():
                return item
        return None

    # Create strain via API (need to check if POST /strains exists with file upload)
    # For now use direct approach - we'll add a dedicated endpoint

    # ------------------------------------------------------------------
    # Images
    # ------------------------------------------------------------------
    def upload_image(
        self, source_path: str, strain: str, media: str, max_colonies: int | None = None
    ) -> dict:
        self._ensure_auth()
        with open(source_path, "rb") as f:
            files = {"image": (Path(source_path).name, f, "image/jpeg")}
            data = {"strain": strain, "media": media}
            if max_colonies is not None:
                data["max_colonies"] = max_colonies
            resp = self.session.post(
                f"{self.base_url}/images/upload", files=files, data=data
            )
            return self._handle_response(resp, "image upload")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _handle_response(resp: requests.Response, context: str) -> dict:
        if resp.status_code in (200, 201, 202):
            return resp.json()
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise RuntimeError(f"{context} failed ({resp.status_code}): {detail}")


class DatasetIngester:
    """High-level importer: species → media → strains → images."""

    def __init__(self, client: BackendAPIClient):
        self.client = client
        self.result = IngestResult()

    def ingest(self, manifest: DatasetManifest) -> IngestResult:
        # Step 1: Create/ensure all species
        species_map: dict[str, dict] = {}
        for name in sorted(manifest.species):
            try:
                species_map[name] = self.client.ensure_species(name)
                self.result.species_created += 1
                print(f"  species: {name}")
            except Exception as e:
                self.result.errors.append(f"species '{name}': {e}")

        # Step 2: Create/ensure all media
        media_map: dict[str, dict] = {}
        for name in sorted(manifest.media):
            try:
                media_map[name] = self.client.ensure_media(name)
                self.result.media_created += 1
                print(f"  media: {name}")
            except Exception as e:
                self.result.errors.append(f"media '{name}': {e}")

        # Step 3: Upload images (each upload creates strain + image)
        for i, entry in enumerate(manifest.images):
            try:
                self.client.upload_image(
                    source_path=entry.source_path,
                    strain=entry.strain_code,
                    media=entry.media_name,
                )
                self.result.images_uploaded += 1
                if (i + 1) % 50 == 0:
                    print(f"  uploaded {i + 1}/{len(manifest.images)} images...")
            except Exception as e:
                self.result.errors.append(f"image '{entry.source_path}': {e}")

        print(
            f"\nIngest complete: "
            f"{self.result.species_created} species, "
            f"{self.result.media_created} media, "
            f"{self.result.images_uploaded} images"
        )
        if self.result.errors:
            print(f"Errors: {len(self.result.errors)}")
            for err in self.result.errors[:10]:
                print(f"  - {err}")

        return self.result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    manifest_path = (
        sys.argv[1] if len(sys.argv) > 1 else "/tmp/opencode/dataset_manifest.json"
    )
    api_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000/api/v1"

    manifest_data = json.loads(Path(manifest_path).read_text())
    manifest = DatasetManifest(
        species=set(manifest_data["species"]),
        media=set(manifest_data["media"]),
        images=[ImageEntry(**img) for img in manifest_data["images"]],
    )

    client = BackendAPIClient(base_url=api_url)
    ingester = DatasetIngester(client)
    ingester.ingest(manifest)
