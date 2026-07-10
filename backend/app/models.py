from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

BIGINT_PK = BigInteger().with_variant(Integer, "sqlite")


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(160))
    role: Mapped[str] = mapped_column(String(32), index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_provider: Mapped[str] = mapped_column(String(32), default="local")
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    sessions: Mapped[list[AuthSession]] = relationship(
        "AuthSession", back_populates="user", cascade="all, delete-orphan"
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="sessions")


class Category(TimestampMixin, Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list)
    included_items: Mapped[list[str]] = mapped_column(JSON, default=list)
    excluded_items: Mapped[list[str]] = mapped_column(JSON, default=list)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    workflow_status: Mapped[str] = mapped_column(String(32), default="data_preparation", index=True)

    parent: Mapped[Category | None] = relationship(
        "Category", remote_side="Category.id", back_populates="children"
    )
    children: Mapped[list[Category]] = relationship("Category", back_populates="parent")
    sections: Mapped[list[EncyclopediaSection]] = relationship(
        "EncyclopediaSection", back_populates="category", cascade="all, delete-orphan"
    )


class ListingSnapshot(TimestampMixin, Base):
    __tablename__ = "listing_snapshots"
    __table_args__ = (
        UniqueConstraint("marketplace", "asin", "scraped_at", name="uq_listing_snapshot"),
        Index("ix_listing_category_brand", "category_id", "brand"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    marketplace: Mapped[str] = mapped_column(String(16), default="US", index=True)
    asin: Mapped[str] = mapped_column(String(20), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    title: Mapped[str] = mapped_column(Text, default="")
    brand: Mapped[str] = mapped_column(String(255), default="", index=True)
    rating_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    rating_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    bsr_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bsr_category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bullet_points: Mapped[list[Any]] = mapped_column(JSON, default=list)
    product_info: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    images: Mapped[Any] = mapped_column(JSON, default=dict)
    videos: Mapped[Any] = mapped_column(JSON, default=dict)
    customers_say: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    qa_content: Mapped[list[Any]] = mapped_column(JSON, default=list)
    aplus_content: Mapped[Any] = mapped_column(JSON, default=dict)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON)

    category: Mapped[Category] = relationship("Category")


class SourceMaterial(TimestampMixin, Base):
    __tablename__ = "source_materials"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_by: Mapped[str] = mapped_column(String(120))

    category: Mapped[Category] = relationship("Category")


class EncyclopediaSection(TimestampMixin, Base):
    __tablename__ = "encyclopedia_sections"
    __table_args__ = (UniqueConstraint("category_id", "section_key", name="uq_category_section"),)

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    section_key: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(160))
    content: Mapped[str] = mapped_column(Text, default="")
    generation_mode: Mapped[str] = mapped_column(String(32), default="empty")
    locked_by_human: Mapped[bool] = mapped_column(Boolean, default=False)
    review_status: Mapped[str] = mapped_column(String(32), default="draft")
    updated_by: Mapped[str | None] = mapped_column(String(120), nullable=True)

    category: Mapped[Category] = relationship("Category", back_populates="sections")
    evidence: Mapped[list[EvidenceLink]] = relationship(
        "EvidenceLink", back_populates="section", cascade="all, delete-orphan"
    )


class EvidenceLink(TimestampMixin, Base):
    __tablename__ = "evidence_links"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("encyclopedia_sections.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[int] = mapped_column(BigInteger)
    locator: Mapped[str | None] = mapped_column(String(500), nullable=True)
    support_type: Mapped[str] = mapped_column(String(32), default="supports")

    section: Mapped[EncyclopediaSection] = relationship(
        "EncyclopediaSection", back_populates="evidence"
    )


class EncyclopediaVersion(TimestampMixin, Base):
    __tablename__ = "encyclopedia_versions"
    __table_args__ = (UniqueConstraint("category_id", "version_number", name="uq_category_version"),)

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), index=True)
    content_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_by: Mapped[str] = mapped_column(String(120))
    reviewed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    category: Mapped[Category] = relationship("Category")


class ImportJob(TimestampMixin, Base):
    __tablename__ = "import_jobs"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    source_path: Mapped[str] = mapped_column(Text)
    requested_directories: Mapped[list[str]] = mapped_column(JSON, default=list)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    inserted_count: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_by: Mapped[str] = mapped_column(String(120))


class TrendSignal(TimestampMixin, Base):
    """每日采集的结构化趋势信号，关联到品类和百科 section。

    存储来自 Google Trends、Amazon Best Sellers 排名变化、社媒热度等
    可量化、可追踪时间维度的信号数据。
    """

    __tablename__ = "trend_signals"
    __table_args__ = (
        Index("ix_trend_category_platform", "category_id", "platform"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    section_key: Mapped[str] = mapped_column(String(80), index=True)
    signal_type: Mapped[str] = mapped_column(String(40), index=True)
    platform: Mapped[str] = mapped_column(String(40), index=True)
    keyword: Mapped[str] = mapped_column(String(500), default="")
    title: Mapped[str] = mapped_column(String(500), default="")
    metric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    metric_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    trend_direction: Mapped[str | None] = mapped_column(String(16), nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )

    category: Mapped[Category] = relationship("Category")


class HotLink(TimestampMixin, Base):
    """热点 / 爆品 / 讨论帖文的结构化跳转链接。

    当爬取 agent 发现热点或爆品时，将跳转链接写入此表，
    关联到品类和百科 section，供业务方一键跳转查看。
    """

    __tablename__ = "hot_links"
    __table_args__ = (
        Index("ix_hotlink_category_platform", "category_id", "platform"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    section_key: Mapped[str] = mapped_column(String(80), index=True)
    link_type: Mapped[str] = mapped_column(String(40), index=True)
    platform: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(500), default="")
    url: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")
    hotness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_hot: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )

    category: Mapped[Category] = relationship("Category")


class PublicationRecord(TimestampMixin, Base):
    __tablename__ = "publication_records"
    __table_args__ = (UniqueConstraint("provider", "version_id", name="uq_provider_version"),)

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("encyclopedia_versions.id"), index=True)
    provider: Mapped[str] = mapped_column(String(32))
    external_doc_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    preview_content: Mapped[str] = mapped_column(Text, default="")
    published_by: Mapped[str] = mapped_column(String(120))


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(String(120), index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[str] = mapped_column(String(80), index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
