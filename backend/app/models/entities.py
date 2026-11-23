"""Relational schema. All tables use integer primary keys, explicit foreign keys and indexes."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """A timestamp that always comes back timezone-aware (UTC).

    SQLite drops the timezone, so without this a value read from the database is serialised as "2026-11-21T08:21:37"
    with no offset, and a browser outside UTC would read it as local time and show the wrong hour."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


def as_utc(dt: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; treat them as UTC."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class Role(Base):
    """The roles an account can have. Kept in its own table so a role is a checked reference, not free text."""

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(20), primary_key=True)
    description: Mapped[str] = mapped_column(String(255))


ROLES = {
    "user": "Can analyse content and manage their own account and history.",
    "admin": "Can also manage accounts, review feedback, read the audit log and see model status.",
}


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(120))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(ForeignKey("roles.name"), default="user", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    avatar_path: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    # Set when the password changes. Tokens carry a "password version" derived from it, so old sessions stop working.
    password_changed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())

    analyses: Mapped[list["AnalysisResult"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class RevokedToken(Base):
    """Logged-out JWTs. A token whose jti is listed here is rejected until it expires."""

    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)  # sha256 of the token, never the token itself
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime())
    used_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"
    __table_args__ = (UniqueConstraint("name", "version", name="uq_dataset_name_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    version: Mapped[str] = mapped_column(String(60))
    source: Mapped[str | None] = mapped_column(String(255))
    language: Mapped[str | None] = mapped_column(String(20))
    num_samples: Mapped[int | None] = mapped_column(Integer)
    label_distribution: Mapped[dict | None] = mapped_column(JSON)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class ModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (UniqueConstraint("module", "name", "version", name="uq_model_module_name_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module: Mapped[str] = mapped_column(String(40), index=True)  # text | image | video | multimodal ...
    name: Mapped[str] = mapped_column(String(120))
    version: Mapped[str] = mapped_column(String(60))
    # trained_baseline | pretrained | heuristic | experimental | unavailable
    status: Mapped[str] = mapped_column(String(30))
    artifact_path: Mapped[str | None] = mapped_column(String(255))
    metrics: Mapped[dict | None] = mapped_column(JSON)
    dataset_version_id: Mapped[int | None] = mapped_column(ForeignKey("dataset_versions.id", ondelete="SET NULL"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    dataset_version: Mapped[DatasetVersion | None] = relationship()


class NewsSubmission(Base):
    __tablename__ = "news_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    submission_type: Mapped[str] = mapped_column(String(20))  # text | image | video | multimodal | url
    headline: Mapped[str | None] = mapped_column(String(500))
    content: Mapped[str | None] = mapped_column(Text)
    content_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    media_filename: Mapped[str | None] = mapped_column(String(255))  # randomised storage name, not the original
    original_filename: Mapped[str | None] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    __table_args__ = (Index("ix_analysis_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("news_submissions.id", ondelete="CASCADE"))
    analysis_type: Mapped[str] = mapped_column(String(20), index=True)  # text | image | video | multimodal
    # Likely Real | Likely Fake | Misleading | Unverified / Insufficient Evidence | Indicators Only
    verdict: Mapped[str] = mapped_column(String(60), index=True)
    confidence: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    model_version_id: Mapped[int | None] = mapped_column(ForeignKey("model_versions.id", ondelete="SET NULL"))
    details: Mapped[dict | None] = mapped_column(JSON)
    limitations: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, index=True)

    user: Mapped[User] = relationship(back_populates="analyses")
    submission: Mapped[NewsSubmission] = relationship()
    model_version: Mapped[ModelVersion | None] = relationship()
    text_prediction: Mapped["TextPrediction | None"] = relationship(back_populates="analysis", uselist=False, cascade="all, delete-orphan")
    image_prediction: Mapped["ImagePrediction | None"] = relationship(back_populates="analysis", uselist=False, cascade="all, delete-orphan")


class TextPrediction(Base):
    __tablename__ = "text_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analysis_results.id", ondelete="CASCADE"), unique=True)
    prob_fake: Mapped[float] = mapped_column(Float)
    prob_real: Mapped[float] = mapped_column(Float)
    token_count: Mapped[int] = mapped_column(Integer)
    language: Mapped[str | None] = mapped_column(String(20))
    top_features: Mapped[list | None] = mapped_column(JSON)

    analysis: Mapped[AnalysisResult] = relationship(back_populates="text_prediction")


class ImagePrediction(Base):
    """Forensic indicators for an uploaded image (error-level analysis and metadata). Not a classifier."""

    __tablename__ = "image_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analysis_results.id", ondelete="CASCADE"), unique=True)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    image_format: Mapped[str] = mapped_column(String(10))
    ela_mean: Mapped[float | None] = mapped_column(Float)
    ela_max: Mapped[float | None] = mapped_column(Float)
    ela_block_cv: Mapped[float | None] = mapped_column(Float)
    heatmap_filename: Mapped[str | None] = mapped_column(String(255))
    metadata_summary: Mapped[dict | None] = mapped_column(JSON)

    analysis: Mapped[AnalysisResult] = relationship(back_populates="image_prediction")


class Claim(Base):
    """Schema for the planned evidence-verification module. Not populated by the current build."""

    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analysis_results.id", ondelete="CASCADE"), index=True)
    claim_text: Mapped[str] = mapped_column(Text)
    verdict: Mapped[str | None] = mapped_column(String(60))


class EvidenceSource(Base):
    """Schema for the planned evidence-verification module. Never filled with invented sources."""

    __tablename__ = "evidence_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(1000))
    title: Mapped[str | None] = mapped_column(String(500))
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    stance: Mapped[str | None] = mapped_column(String(20))  # supports | contradicts | related
    relevance: Mapped[float | None] = mapped_column(Float)


class UserFeedback(Base):
    __tablename__ = "user_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    analysis_id: Mapped[int | None] = mapped_column(ForeignKey("analysis_results.id", ondelete="SET NULL"))
    category: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="new", index=True)  # new | reviewed | dismissed
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(60), index=True)
    entity: Mapped[str | None] = mapped_column(String(40))
    entity_id: Mapped[str | None] = mapped_column(String(40))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    detail: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, index=True)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)
