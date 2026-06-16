import datetime
import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from ..database import Base


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="user", server_default="user"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    retrieval_jobs: Mapped[list["RetrievalJob"]] = relationship(back_populates="user")
    feedbacks_submitted: Mapped[list["Feedback"]] = relationship(
        back_populates="submitter", foreign_keys="Feedback.submitter_id"
    )
    feedbacks_reviewed: Mapped[list["Feedback"]] = relationship(
        back_populates="reviewer", foreign_keys="Feedback.reviewer_id"
    )
    training_jobs: Mapped[list["TrainingJob"]] = relationship(
        back_populates="triggered_by_user"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class Media(Base):
    __tablename__ = "media"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    archived_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    images: Mapped[list["Image"]] = relationship(back_populates="media")


class Species(Base):
    __tablename__ = "species"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    archived_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    strains: Mapped[list["Strain"]] = relationship(
        back_populates="species", cascade="all, delete-orphan"
    )
    images: Mapped[list["Image"]] = relationship(back_populates="species")


class Strain(Base):
    __tablename__ = "strains"
    __table_args__ = (
        UniqueConstraint("name", "species_id", name="uq_strain_name_species"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    species_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("species.id"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    archived_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    species: Mapped["Species"] = relationship(back_populates="strains")
    images: Mapped[list["Image"]] = relationship(
        back_populates="strain", cascade="all, delete-orphan"
    )


class Image(Base):
    __tablename__ = "images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    strain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("strains.id"), nullable=False
    )
    species_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("species.id"), nullable=False
    )
    media_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media.id"), nullable=False
    )
    angle: Mapped[str | None] = mapped_column(String(10), nullable=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    prepared_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pipeline_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    data_update_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="current", server_default="current"
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    archived_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    strain: Mapped["Strain"] = relationship(back_populates="images")
    species: Mapped["Species"] = relationship(back_populates="images")
    media: Mapped["Media"] = relationship(back_populates="images")
    segments: Mapped[list["Segment"]] = relationship(
        back_populates="image", cascade="all, delete-orphan"
    )
    feedbacks: Mapped[list["Feedback"]] = relationship(back_populates="image")


class Segment(Base):
    __tablename__ = "segments"
    __table_args__ = (
        UniqueConstraint("image_id", "segment_index", name="uq_segment_image_index"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("images.id"), nullable=False
    )
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)
    crop_path: Mapped[str] = mapped_column(String(500), nullable=False)
    bbox_x: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_y: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_w: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_h: Mapped[int] = mapped_column(Integer, nullable=False)
    segmentation_method: Mapped[str] = mapped_column(String(20), nullable=False)
    qdrant_point_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    image: Mapped["Image"] = relationship(back_populates="segments")
    qdrant_index_state: Mapped["QdrantIndexState | None"] = relationship(
        back_populates="segment", uselist=False
    )


class RetrievalJob(Base):
    __tablename__ = "retrieval_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    job_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )
    config: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )
    input_summary: Mapped[dict[str, object] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="retrieval_jobs")
    results: Mapped[list["RetrievalResult"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class RetrievalResult(Base):
    __tablename__ = "retrieval_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("retrieval_jobs.id"), nullable=False
    )
    strain_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    species_name: Mapped[str] = mapped_column(String(255), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)

    job: Mapped["RetrievalJob"] = relationship(back_populates="results")
    neighbors: Mapped[list["RetrievalNeighbor"]] = relationship(
        back_populates="result", cascade="all, delete-orphan"
    )
    feedbacks: Mapped[list["Feedback"]] = relationship(back_populates="result")


class RetrievalNeighbor(Base):
    __tablename__ = "retrieval_neighbors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_results.id"),
        nullable=False,
    )
    neighbor_strain: Mapped[str] = mapped_column(String(255), nullable=False)
    neighbor_species: Mapped[str] = mapped_column(String(255), nullable=False)
    similarity: Mapped[float] = mapped_column(Float, nullable=False)
    media: Mapped[str] = mapped_column(String(20), nullable=False)
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)

    result: Mapped["RetrievalResult"] = relationship(back_populates="neighbors")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    submitter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="retrieval_result",
        server_default="retrieval_result",
    )
    feedback_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="wrong_prediction",
        server_default="wrong_prediction",
    )
    query_strain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_results.id"),
        nullable=True,
    )
    image_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("images.id"), nullable=True
    )
    predicted_species: Mapped[str | None] = mapped_column(String(255), nullable=True)
    suggested_species: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reviewed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    submitter: Mapped["User"] = relationship(
        back_populates="feedbacks_submitted", foreign_keys=[submitter_id]
    )
    reviewer: Mapped["User | None"] = relationship(
        back_populates="feedbacks_reviewed", foreign_keys=[reviewer_id]
    )
    result: Mapped["RetrievalResult | None"] = relationship(back_populates="feedbacks")
    image: Mapped["Image | None"] = relationship(back_populates="feedbacks")


class TrainingJob(Base):
    __tablename__ = "training_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    triggered_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    job_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )
    progress: Mapped[dict[str, object] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    changes_since_last: Mapped[dict[str, object] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_deployed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    started_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    triggered_by_user: Mapped["User"] = relationship(back_populates="training_jobs")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    changes: Mapped[dict[str, object] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    ip_address: Mapped[str | None] = mapped_column(
        INET().with_variant(String(45), "sqlite"), nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="audit_logs")


class QdrantIndexState(Base):
    __tablename__ = "qdrant_index_state"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    segment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("segments.id"), nullable=False
    )
    qdrant_point_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    collection_name: Mapped[str] = mapped_column(String(100), nullable=False)
    indexed_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_updated: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    segment: Mapped["Segment"] = relationship(back_populates="qdrant_index_state")


class SystemState(Base):
    __tablename__ = "system_state"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class InviteToken(Base):
    __tablename__ = "invite_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    is_used: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
