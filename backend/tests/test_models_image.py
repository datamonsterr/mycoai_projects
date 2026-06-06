import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mycoai_retrieval_backend.models import (
    Image,
    Media,
    Segment,
    Species,
    Strain,
)


@pytest.mark.asyncio
@pytest.mark.skip(reason="SQLite does not enforce FK constraints by default")
async def test_image_requires_species_and_media_fks(session: AsyncSession) -> None:
    species = Species(name="Fusarium oxysporum")
    session.add(species)
    await session.flush()

    strain = Strain(name="Fo-47", species_id=species.id, source="curated_primary")
    session.add(strain)
    await session.flush()

    image = Image(
        strain_id=strain.id,
        species_id=species.id,
        media_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
        file_path="images/test.jpg",
    )
    session.add(image)

    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_image_data_update_status_defaults_to_current(
    session: AsyncSession,
) -> None:
    species = Species(name="Trichoderma harzianum")
    session.add(species)
    await session.flush()

    strain = Strain(name="T22", species_id=species.id, source="curated_primary")
    session.add(strain)
    await session.flush()

    media = Media(name="CMA-Corn Meal Agar")
    session.add(media)
    await session.flush()

    image = Image(
        strain_id=strain.id,
        species_id=species.id,
        media_id=media.id,
        file_path="images/t22.jpg",
    )
    session.add(image)
    await session.commit()

    loaded = (
        await session.execute(select(Image).where(Image.file_path == "images/t22.jpg"))
    ).scalar_one()
    assert loaded.data_update_status == "current"


@pytest.mark.asyncio
async def test_image_archive(session: AsyncSession) -> None:
    species = Species(name="Botrytis cinerea")
    session.add(species)
    await session.flush()

    strain = Strain(name="B05.10", species_id=species.id, source="curated_primary")
    session.add(strain)
    await session.flush()

    media = Media(name="V8 Juice Agar")
    session.add(media)
    await session.flush()

    image = Image(
        strain_id=strain.id,
        species_id=species.id,
        media_id=media.id,
        file_path="images/botrytis.jpg",
    )
    session.add(image)
    await session.commit()

    loaded = (
        await session.execute(
            select(Image).where(Image.file_path == "images/botrytis.jpg")
        )
    ).scalar_one()
    loaded.is_archived = True
    await session.commit()

    reloaded = (
        await session.execute(
            select(Image).where(Image.file_path == "images/botrytis.jpg")
        )
    ).scalar_one()
    assert reloaded.is_archived is True


@pytest.mark.asyncio
async def test_image_segments_relationship(session: AsyncSession) -> None:
    species = Species(name="Alternaria alternata")
    session.add(species)
    await session.flush()

    strain = Strain(name="Aa-1", species_id=species.id, source="user_upload")
    session.add(strain)
    await session.flush()

    media = Media(name="MEA")
    session.add(media)
    await session.flush()

    image = Image(
        strain_id=strain.id,
        species_id=species.id,
        media_id=media.id,
        file_path="images/alternaria.jpg",
    )
    session.add(image)
    await session.flush()

    segment = Segment(
        image_id=image.id,
        segment_index=0,
        crop_path="crops/alt_0.jpg",
        bbox_x=10,
        bbox_y=20,
        bbox_w=50,
        bbox_h=50,
        segmentation_method="kmeans",
    )
    session.add(segment)
    await session.commit()

    loaded = (
        await session.execute(
            select(Image)
            .where(Image.file_path == "images/alternaria.jpg")
            .options(selectinload(Image.segments))
        )
    ).scalar_one()
    assert len(loaded.segments) == 1
    assert loaded.segments[0].segmentation_method == "kmeans"
    assert loaded.segments[0].crop_path == "crops/alt_0.jpg"


@pytest.mark.asyncio
async def test_image_angle_field(session: AsyncSession) -> None:
    species = Species(name="Mucor mucedo")
    session.add(species)
    await session.flush()

    strain = Strain(name="Mm-1", species_id=species.id, source="curated_primary")
    session.add(strain)
    await session.flush()

    media = Media(name="WA-Water Agar")
    session.add(media)
    await session.flush()

    image = Image(
        strain_id=strain.id,
        species_id=species.id,
        media_id=media.id,
        angle="90",
        file_path="images/mucor.jpg",
    )
    session.add(image)
    await session.commit()

    loaded = (
        await session.execute(select(Image).where(Image.angle == "90"))
    ).scalar_one()
    assert loaded.angle == "90"
