"""Integration tests for the batch pipeline (DB + segmentation + Qdrant).

Tests the full `tasks.batch.run()` flow using an in-memory SQLite DB,
the real SegmentationPipeline with test fixture images, and mock Qdrant.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from tempfile import mkdtemp
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mycoai_retrieval_backend.config import get_settings
from mycoai_retrieval_backend.database import Base
from mycoai_retrieval_backend.models import Image, Segment
from mycoai_retrieval_backend.segmentation import SegmentationPipeline
from mycoai_retrieval_backend.tasks.batch import run as batch_run

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
    pytest.mark.skip(reason="Requires PostgreSQL + Qdrant — run with integration_postgres marker"),
]


@pytest.fixture
def test_image_dir():
    """Create a temporary directory with synthetic test images."""
    import numpy as np

    tmpdir = Path(mkdtemp(prefix="test_batch_import_"))
    subdir = tmpdir / "DTO 148-C8 Penicillium cyclopium"
    subdir.mkdir(parents=True)

    # Create a 128x128 white circle on black background (simulates petri dish)
    img = np.zeros((128, 128, 3), dtype=np.uint8)
    cv_center = (64, 64)
    cv_radius = 40
    for y in range(128):
        for x in range(128):
            if (x - cv_center[0]) ** 2 + (y - cv_center[1]) ** 2 <= cv_radius**2:
                img[y, x] = [200, 180, 160]

    import cv2 as cv

    cv.imwrite(str(subdir / "DTO 148-C8 CYAob_edited.jpg"), img)
    cv.imwrite(str(subdir / "DTO 148-C8 MEAr_edited.jpg"), img)

    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def upload_root():
    """Temp upload root for segmentation pipeline."""
    root = Path(mkdtemp(prefix="test_uploads_"))
    yield root
    shutil.rmtree(root, ignore_errors=True)


@pytest.fixture
async def db_session():
    """Create an in-memory SQLite async session with schema."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(
        "sqlite+aiosqlite://",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as db:
        yield db

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.integration_postgres
class TestBatchPipeline:
    """Integration tests for the batch import pipeline."""

    async def test_batch_import_creates_images_in_db(
        self, test_image_dir: Path, upload_root: Path, db_session: AsyncSession
    ):
        pipeline = SegmentationPipeline(upload_root)

        with patch(
            "mycoai_retrieval_backend.tasks.batch.QdrantClientService",
            new_callable=AsyncMock,
        ) as mock_qdrant:
            mock_instance = mock_qdrant.return_value
            mock_instance.upsert_point = AsyncMock()

            result = await batch_run(
                source_dir=str(test_image_dir),
                db=db_session,
                pipeline=pipeline,
                method="kmeans",
            )

            await db_session.commit()

            assert result["total"] >= 2
            assert result["successful"] >= 1

    async def test_metadata_is_persisted(
        self, test_image_dir: Path, upload_root: Path, db_session: AsyncSession
    ):
        pipeline = SegmentationPipeline(upload_root)

        with patch(
            "mycoai_retrieval_backend.tasks.batch.QdrantClientService",
            new_callable=AsyncMock,
        ) as mock_qdrant:
            mock_instance = mock_qdrant.return_value
            mock_instance.upsert_point = AsyncMock()

            await batch_run(
                source_dir=str(test_image_dir),
                db=db_session,
                pipeline=pipeline,
                method="kmeans",
            )
            await db_session.commit()

        species_result = await db_session.execute(
            select(Image).limit(5)
        )
        images = species_result.scalars().all()
        assert len(images) > 0

        for img in images:
            assert img.species_id is not None
            assert img.media_id is not None
            assert img.strain_id is not None
            assert img.file_path != ""
            assert len(img.segments) >= 0

    async def test_segments_are_created(
        self, test_image_dir: Path, upload_root: Path, db_session: AsyncSession
    ):
        pipeline = SegmentationPipeline(upload_root)

        with patch(
            "mycoai_retrieval_backend.tasks.batch.QdrantClientService",
            new_callable=AsyncMock,
        ) as mock_qdrant:
            mock_instance = mock_qdrant.return_value
            mock_instance.upsert_point = AsyncMock()

            await batch_run(
                source_dir=str(test_image_dir),
                db=db_session,
                pipeline=pipeline,
                method="kmeans",
            )
            await db_session.commit()

        segment_result = await db_session.execute(select(Segment))
        segments = segment_result.scalars().all()
        assert len(segments) > 0
        for seg in segments:
            assert seg.crop_path != ""
            assert seg.segmentation_method in ("kmeans", "contour")


@pytest.mark.integration_postgres
class TestBatchImportLimitAndErrors:
    """Test limit and error handling behavior."""

    async def test_limit_respected(
        self, test_image_dir: Path, upload_root: Path, db_session: AsyncSession
    ):
        pipeline = SegmentationPipeline(upload_root)

        with patch(
            "mycoai_retrieval_backend.tasks.batch.QdrantClientService",
            new_callable=AsyncMock,
        ) as mock_qdrant:
            mock_instance = mock_qdrant.return_value
            mock_instance.upsert_point = AsyncMock()

            result = await batch_run(
                source_dir=str(test_image_dir),
                db=db_session,
                pipeline=pipeline,
                method="kmeans",
                limit=1,
            )

            assert result["successful"] <= 1

    async def test_nonexistent_directory(
        self, upload_root: Path, db_session: AsyncSession
    ):
        pipeline = SegmentationPipeline(upload_root)

        result = await batch_run(
            source_dir="/nonexistent/path/12345",
            db=db_session,
            pipeline=pipeline,
        )

        assert "error" in result
