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

    parent: Mapped[Category | None] = relationship(
        "Category", remote_side="Category.id", back_populates="children"
    )
    children: Mapped[list[Category]] = relationship("Category", back_populates="parent")
    sections: Mapped[list[EncyclopediaSection]] = relationship(
        "EncyclopediaSection", back_populates="category", cascade="all, delete-orphan"
    )


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
    title_zh: Mapped[str | None] = mapped_column(String(200), nullable=True)
    metric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    metric_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    trend_direction: Mapped[str | None] = mapped_column(String(16), nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    summary_zh: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    title_zh: Mapped[str | None] = mapped_column(String(200), nullable=True)
    url: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")
    description_zh: Mapped[str | None] = mapped_column(Text, nullable=True)
    hotness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_hot: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )

    category: Mapped[Category] = relationship("Category")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(String(120), index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[str] = mapped_column(String(80))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AgentScan(TimestampMixin, Base):
    """选品Agent的一次扫描会话。

    记录扫描的类型(全站/指定品类/自由话题)、LLM生成的分析报告、
    以及扫描时收集的数据快照。
    """

    __tablename__ = "agent_scans"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    scan_type: Mapped[str] = mapped_column(String(40), index=True)  # full|category|topic
    category_code: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    topic: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running", index=True)  # running|completed|failed
    triggered_by: Mapped[str] = mapped_column(String(120))
    # LLM生成的结构化分析报告
    report: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # 扫描期间收集的原始数据摘要
    data_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # 扫描期间收集的统计
    stats: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    discoveries: Mapped[list["ProductDiscovery"]] = relationship(
        "ProductDiscovery", back_populates="scan", cascade="all, delete-orphan"
    )
    messages: Mapped[list["AgentMessage"]] = relationship(
        "AgentMessage", back_populates="scan", cascade="all, delete-orphan"
    )


class ProductDiscovery(TimestampMixin, Base):
    """选品Agent发现的产品/机会点。

    每个发现包含：产品名称、品类、市场信号、机会评分、推荐理由、
    来源数据（Amazon BSR排名、趋势关键词、社媒热度等）。
    """

    __tablename__ = "product_discoveries"
    __table_args__ = (
        Index("ix_discovery_scan_opportunity", "scan_id", "opportunity_type"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("agent_scans.id"), index=True)
    # 产品/机会名称
    product_name: Mapped[str] = mapped_column(String(500))
    # 关联品类code (可为空，代表新品类)
    category_code: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    # 机会类型: hot_product|rising_trend|gap_opportunity|emerging_category
    opportunity_type: Mapped[str] = mapped_column(String(40), index=True)
    # LLM评估的机会评分 0-100
    opportunity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 推荐理由
    reasoning: Mapped[str] = mapped_column(Text, default="")
    # 市场信号数据（BSR、价格、评分等）
    market_signals: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # 趋势关键词
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    # 来源链接
    source_links: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    # 状态: new|reviewed|selected|archived
    status: Mapped[str] = mapped_column(String(32), default="new", index=True)
    # 用户备注
    user_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    scan: Mapped["AgentScan"] = relationship("AgentScan", back_populates="discoveries")


class AgentMessage(TimestampMixin, Base):
    """选品Agent与用户的对话消息流。

    支持多轮对话：用户可以追问Agent的发现，请求深入分析某个产品等。
    """

    __tablename__ = "agent_messages"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("agent_scans.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # user|assistant
    content: Mapped[str] = mapped_column(Text, default="")
    # 附带的LLM元数据（模型、token用量等）
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    scan: Mapped["AgentScan"] = relationship("AgentScan", back_populates="messages")
