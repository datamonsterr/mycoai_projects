from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Image, Media, Species, Strain


@pytest.fixture(name="headers")
def fixture_headers(client: TestClient) -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@mycoai.dev", "password": "password123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_media_delete_impact_counts_images(
    session: AsyncSession,
    client: TestClient,
    headers: dict[str, str],
) -> None:
    media = Media(name="WARN_MEDIA")
    species = Species(name="Warn Species")
    session.add_all([media, species])
    await session.flush()
    strain = Strain(name="WARN_STRAIN", species_id=species.id, source="test")
    session.add(strain)
    await session.flush()
    session.add(
        Image(
            strain_id=strain.id,
            species_id=species.id,
            media_id=media.id,
            file_path="warn.jpg",
        )
    )
    await session.commit()

    response = client.get(f"/api/v1/media/{media.id}/delete-impact", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["strain_count"] == 1
    assert body["segment_count"] == 0
    assert (
        body["warning_message"]
        == "Archiving this media affects 1 strain(s) and 0 segment(s)."
    )


@pytest.mark.asyncio
async def test_species_delete_impact_counts_images_and_strains(
    session: AsyncSession,
    client: TestClient,
    headers: dict[str, str],
) -> None:
    species = Species(name="Warn Species 2")
    media = Media(name="WARN_MEDIA_2")
    session.add_all([species, media])
    await session.flush()
    strain = Strain(name="WARN_STRAIN_2", species_id=species.id, source="test")
    session.add(strain)
    await session.flush()
    session.add(
        Image(
            strain_id=strain.id,
            species_id=species.id,
            media_id=media.id,
            file_path="warn2.jpg",
        )
    )
    await session.commit()

    response = client.get(
        f"/api/v1/species/{species.id}/delete-impact",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["strain_count"] == 1
    assert body["segment_count"] == 0
    assert (
        body["warning_message"]
        == "Archiving this species affects 1 strain(s) and 0 segment(s)."
    )


@pytest.mark.asyncio
async def test_strain_delete_impact_counts_images(
    session: AsyncSession,
    client: TestClient,
    headers: dict[str, str],
) -> None:
    species = Species(name="Warn Species 3")
    media = Media(name="WARN_MEDIA_3")
    session.add_all([species, media])
    await session.flush()
    strain = Strain(name="WARN_STRAIN_3", species_id=species.id, source="test")
    session.add(strain)
    await session.flush()
    session.add(
        Image(
            strain_id=strain.id,
            species_id=species.id,
            media_id=media.id,
            file_path="warn3.jpg",
        )
    )
    await session.commit()

    response = client.get(
        f"/api/v1/strains/{strain.id}/delete-impact",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["segment_count"] == 0
    assert body["warning_message"] == "Archiving this strain affects 0 segment(s)."
