from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


Role = Literal["admin", "data", "researcher", "reviewer"]


class LocalLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=1, max_length=256)


class CategoryUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=10000)
    aliases: list[str] | None = None
    included_items: list[str] | None = None
    excluded_items: list[str] | None = None


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


class SectionUpdate(BaseModel):
    content: str = Field(max_length=200000)
    evidence_source_ids: list[int] = Field(default_factory=list, max_length=100)
    generation_mode: Literal["human", "generated"] = "human"


class TrendSignalCreate(BaseModel):
    category_code: str
    section_key: str = Field(max_length=80)
    signal_type: Literal[
        "search_volume", "best_seller_rank", "social_mention",
        "keyword_trend", "news_volume", "review_sentiment",
        "product_insight", "user_pain_point",
    ]
    platform: Literal[
        "google", "amazon", "reddit", "youtube", "tiktok",
        "xiaohongshu", "x", "facebook", "news", "other",
    ]
    keyword: str = Field(default="", max_length=500)
    title: str = Field(default="", max_length=500)
    title_zh: str | None = Field(default=None, max_length=200)
    metric_value: float | None = None
    metric_unit: str | None = Field(default=None, max_length=32)
    trend_direction: Literal["up", "down", "stable", "new", "positive", "negative", "mixed"] | None = None
    summary: str = Field(default="", max_length=10000)
    summary_zh: str | None = Field(default=None, max_length=10000)


class HotLinkCreate(BaseModel):
    category_code: str
    section_key: str = Field(max_length=80)
    link_type: Literal[
        "product", "discussion", "video", "social_post", "news", "trend", "keyword",
    ]
    platform: Literal[
        "google", "amazon", "reddit", "youtube", "tiktok",
        "xiaohongshu", "x", "facebook", "news", "other",
    ]
    title: str = Field(default="", max_length=500)
    title_zh: str | None = Field(default=None, max_length=200)
    url: HttpUrl
    description: str = Field(default="", max_length=10000)
    description_zh: str | None = Field(default=None, max_length=10000)
    hotness_score: float | None = None
    is_hot: bool = False


class TrendSignalBatch(BaseModel):
    items: list[TrendSignalCreate] = Field(min_length=1, max_length=500)


class HotLinkBatch(BaseModel):
    items: list[HotLinkCreate] = Field(min_length=1, max_length=500)


class AgentScanRequest(BaseModel):
    scan_type: Literal["full", "category", "topic"] = "full"
    category_code: str | None = Field(default=None, max_length=80)
    topic: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_scope(self):
        if self.scan_type == "category" and not self.category_code:
            raise ValueError("category 扫描必须指定 category_code")
        if self.scan_type == "topic" and (not self.topic or not self.topic.strip()):
            raise ValueError("topic 扫描必须指定非空 topic")
        if self.scan_type != "category" and self.category_code is not None:
            raise ValueError("只有 category 扫描可以指定 category_code")
        if self.scan_type != "topic" and self.topic is not None:
            raise ValueError("只有 topic 扫描可以指定 topic")
        return self


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)


class DiscoveryUpdateRequest(BaseModel):
    status: Literal["new", "reviewed", "selected", "archived"] | None = None
    user_note: str | None = Field(default=None, max_length=5000)
