from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


Role = Literal["admin", "data", "researcher", "reviewer"]


class LocalLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=1, max_length=256)


class CategoryUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=10000)
    aliases: list[str] | None = None
    included_items: list[str] | None = None
    excluded_items: list[str] | None = None


class AmazonImportRequest(BaseModel):
    root_path: str = "/imports"
    directories: list[str] | None = None


class SourceMaterialCreate(BaseModel):
    category_code: str
    source_type: Literal[
        "internal_doc", "research", "amazon", "search", "social", "media", "manual"
    ]
    title: str = Field(min_length=1, max_length=500)
    url: HttpUrl | None = None
    content: str = Field(default="", max_length=200000)
    published_at: datetime | None = None
    collected_at: datetime | None = None


class DraftRequest(BaseModel):
    listing_limit: int = Field(default=100, ge=1, le=500)
    listing_ids: list[int] = Field(default_factory=list, max_length=500)
    source_material_ids: list[int] = Field(default_factory=list, max_length=100)


class SectionUpdate(BaseModel):
    content: str = Field(max_length=200000)
    evidence_listing_ids: list[int] = Field(default_factory=list, max_length=100)
    evidence_source_ids: list[int] = Field(default_factory=list, max_length=100)
    generation_mode: Literal["human", "generated"] = "human"


class SubmitReviewRequest(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


class ReviewRequest(BaseModel):
    decision: Literal["approve", "reject"]
    comment: str = Field(default="", max_length=5000)

    @field_validator("comment")
    @classmethod
    def rejection_requires_comment(cls, value: str, info):
        if info.data.get("decision") == "reject" and not value.strip():
            raise ValueError("Rejecting a version requires a comment")
        return value


class PublishRequest(BaseModel):
    provider: Literal["local", "feishu"] = "local"


class TrendSignalCreate(BaseModel):
    category_code: str
    section_key: str = Field(max_length=80)
    signal_type: Literal[
        "search_volume", "best_seller_rank", "social_mention",
        "keyword_trend", "news_volume", "review_sentiment",
    ]
    platform: Literal[
        "google", "amazon", "reddit", "youtube", "tiktok",
        "x", "facebook", "news", "other",
    ]
    keyword: str = Field(default="", max_length=500)
    title: str = Field(default="", max_length=500)
    metric_value: float | None = None
    metric_unit: str | None = Field(default=None, max_length=32)
    trend_direction: Literal["up", "down", "stable", "new"] | None = None
    summary: str = Field(default="", max_length=10000)


class HotLinkCreate(BaseModel):
    category_code: str
    section_key: str = Field(max_length=80)
    link_type: Literal[
        "product", "discussion", "video", "news", "trend", "keyword",
    ]
    platform: Literal[
        "google", "amazon", "reddit", "youtube", "tiktok",
        "x", "facebook", "news", "other",
    ]
    title: str = Field(default="", max_length=500)
    url: HttpUrl
    description: str = Field(default="", max_length=10000)
    hotness_score: float | None = None
    is_hot: bool = False


class TrendSignalBatch(BaseModel):
    items: list[TrendSignalCreate] = Field(min_length=1, max_length=500)


class HotLinkBatch(BaseModel):
    items: list[HotLinkCreate] = Field(min_length=1, max_length=500)
