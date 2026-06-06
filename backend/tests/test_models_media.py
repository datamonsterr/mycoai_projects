import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mycoai_retrieval_backend.models import (
    Image,
    Media,
    Species,
    Strain,
)


@pytest.mark.asyncio
async def test_create_media_with_unique_name(session: AsyncSession) -> None:
    media = Media(name="MEA-Malt Extract Agar", description="Standard growth medium")
    session.add(media)
    await session.commit()

    result = (
        await session.execute(
            select(Media).where(Media.name == "MEA-Malt Extract Agar")
        )
    ).scalar_one()
    assert result.name == "MEA-Malt Extract Agar"
    assert result.description == "Standard growth medium"
    assert result.is_archived is False


@pytest.mark.asyncio
async def test_media_duplicate_name_raises(session: AsyncSession) -> None:
    session.add(Media(name="CYA-Czapek Yeast Autolysate"))
    await session.flush()
    session.add(Media(name="CYA-Czapek Yeast Autolysate"))

    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_media_archive_and_restore(session: AsyncSession) -> None:
    media = Media(name="G25N")
    session.add(media)
    await session.commit()

    stored = (
        await session.execute(select(Media).where(Media.name == "G25N"))
    ).scalar_one()
    stored.is_archived = True
    await session.commit()

    reloaded = (
        await session.execute(select(Media).where(Media.name == "G25N"))
    ).scalar_one()
    assert reloaded.is_archived is True

    reloaded.is_archived = False
    await session.commit()

    restored = (
        await session.execute(select(Media).where(Media.name == "G25N"))
    ).scalar_one()
    assert restored.is_archived is False


@pytest.mark.asyncio
async def test_media_relationships(session: AsyncSession) -> None:
    species = Species(name="Aspergillus niger")
    session.add(species)
    await session.flush()

    strain = Strain(name="ATCC 16888", species_id=species.id, source="curated_primary")
    session.add(strain)
    await session.flush()

    media = Media(name="PDA-Potato Dextrose Agar")
    session.add(media)
    await session.flush()

    image = Image(
        strain_id=strain.id,
        species_id=species.id,
        media_id=media.id,
        file_path="images/pda_sample.jpg",
    )
    session.add(image)
    await session.commit()

    loaded = (
        await session.execute(
            select(Media)
            .where(Media.name == "PDA-Potato Dextrose Agar")
            .options(selectinload(Media.images))
        )
    ).scalar_one()
    assert len(loaded.images) == 1
    assert loaded.images[0].file_path == "images/pda_sample.jpg"


@pytest.mark.asyncio
async def test_media_cascade_does_not_delete_images(session: AsyncSession) -> None:
    species = Species(name="Penicillium roqueforti")
    session.add(species)
    await session.flush()

    strain = Strain(name="PR-1", species_id=species.id, source="user_upload")
    session.add(strain)
    await session.flush()

    media = Media(name="YES-Yeast Extract Sucrose")
    session.add(media)
    await session.flush()

    image = Image(
        strain_id=strain.id,
        species_id=species.id,
        media_id=media.id,
        file_path="images/yes_sample.jpg",
    )
    session.add(image)
    await session.commit()

    await session.delete(media)
    with pytest.raises(IntegrityError):
        await session.commit()
