from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.database import get_db
from app.integrations.feishu_auth import (
    authorization_url,
    exchange_code,
    upsert_user,
    verify_state,
)
from app.models import (
    AgentMessage,
    AgentScan,
    Category,
    EncyclopediaSection,
    HotLink,
    ProductDiscovery,
    SourceMaterial,
    TrendSignal,
)
from app.schemas import (
    AgentChatRequest,
    AgentScanRequest,
    AgentScanUpdateRequest,
    CategoryUpdate,
    DiscoveryUpdateRequest,
    HotLinkBatch,
    HotLinkCreate,
    LocalLoginRequest,
    SectionUpdate,
    SourceMaterialCreate,
    TrendSignalBatch,
    TrendSignalCreate,
)
from app.security import (
    Actor,
    authenticate_local,
    create_session,
    ensure_role,
    get_actor,
    revoke_session,
)
from app.services.agent_service import AgentError, chat as agent_chat, chat_stream as agent_chat_stream, run_scan
from app.services.content_service import ContentError, save_section
from app.services.listing_suggestion_service import (
    generate_listing_suggestion_preview,
)
from app.services.market_brief_service import generate_market_brief


router = APIRouter(prefix="/api/v1")
Db = Annotated[Session, Depends(get_db)]
WriteActor = Annotated[Actor, Depends(get_actor)]
ReadActor = Annotated[Actor, Depends(get_actor)]


@router.get("/auth/config")
def auth_config():
    settings = get_settings()
    return {
        "mode": settings.auth_mode,
        "local_enabled": settings.auth_mode == "local" and bool(settings.auth_users_json.strip()),
        "feishu_enabled": settings.auth_mode == "feishu"
        and bool(settings.feishu_app_id and settings.feishu_app_secret),
        "session_cookie_name": settings.session_cookie_name,
    }


@router.get("/auth/feishu/start")
def feishu_login_start():
    if get_settings().auth_mode != "feishu":
        raise HTTPException(status_code=404, detail="飞书登录未启用")
    try:
        return RedirectResponse(authorization_url(), status_code=307)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="飞书登录尚未完成配置") from exc


@router.get("/auth/feishu/callback")
def feishu_login_callback(
    db: Db,
    code: str | None = Query(default=None, max_length=1000),
    state: str | None = Query(default=None, max_length=1000),
):
    settings = get_settings()
    if settings.auth_mode != "feishu":
        raise HTTPException(status_code=404, detail="飞书登录未启用")
    try:
        valid_state = bool(state and verify_state(state))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="飞书登录尚未完成配置") from exc
    if not code or not valid_state:
        raise HTTPException(status_code=400, detail="登录授权已失效，请重新登录")
    try:
        identity = exchange_code(code)
        user = upsert_user(db, identity)
        redirect = RedirectResponse(settings.feishu_frontend_url, status_code=303)
        create_session(db, user, redirect)
        return redirect
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (RuntimeError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=502, detail="飞书登录失败，请稍后重试") from exc


@router.post("/auth/local/login")
def local_login(body: LocalLoginRequest, db: Db, response: Response):
    settings = get_settings()
    if settings.auth_mode != "local":
        raise HTTPException(status_code=404, detail="本地登录未启用")
    user = authenticate_local(db, body.username, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="账号或密码不正确")
    create_session(db, user, response)
    return {"user": {"id": user.id, "name": user.display_name, "role": user.role}}


@router.get("/auth/me")
def auth_me(actor: WriteActor):
    return {"id": actor.id, "name": actor.name, "role": actor.role, "provider": actor.provider}


@router.post("/auth/logout")
def logout(
    db: Db,
    request: Request,
    response: Response,
):
    revoke_session(db, request.cookies.get(get_settings().session_cookie_name))
    response.delete_cookie(get_settings().session_cookie_name, path="/")
    return {"ok": True}


def _category_or_404(db: Session, code: str) -> Category:
    category = db.scalar(
        select(Category)
        .options(
            selectinload(Category.children),
            selectinload(Category.parent),
            selectinload(Category.sections).selectinload(EncyclopediaSection.evidence),
        )
        .where(Category.code == code)
    )
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


def _section_payload(section: EncyclopediaSection, db: Session | None = None) -> dict:
    evidence_payload = []
    for evidence in section.evidence:
        item: dict = {
            "id": evidence.id,
            "source_type": evidence.source_type,
            "source_id": evidence.source_id,
            "locator": evidence.locator,
            "source": None,
        }
        if db is not None and evidence.source_type == "source_material":
            source = db.get(SourceMaterial, evidence.source_id)
            if source is not None:
                item["source"] = {
                    "title": source.title,
                    "source_type": source.source_type,
                    "collected_at": source.collected_at,
                    "published_at": source.published_at,
                    "url": source.url,
                }
        elif db is not None and evidence.source_type == "hot_link":
            source = db.get(HotLink, evidence.source_id)
            if source is not None:
                item["source"] = {
                    "title": source.title_zh or source.title,
                    "source_type": source.platform,
                    "collected_at": source.collected_at,
                    "published_at": None,
                    "url": source.url,
                }
        evidence_payload.append(item)
    return {
        "id": section.id,
        "section_key": section.section_key,
        "title": section.title,
        "content": section.content,
        "generation_mode": section.generation_mode,
        "locked_by_human": section.locked_by_human,
        "updated_by": section.updated_by,
        "updated_at": section.updated_at,
        "evidence": evidence_payload,
    }


def _category_payload(
    category: Category, include_sections: bool = False, db: Session | None = None
) -> dict:
    payload = {
        "id": category.id,
        "code": category.code,
        "name": category.name,
        "description": category.description,
        "aliases": category.aliases,
        "included_items": category.included_items,
        "excluded_items": category.excluded_items,
        "status": category.status,
        "parent_code": category.parent.code if category.parent else None,
        "children": [
            {
                "id": child.id,
                "code": child.code,
                "name": child.name,
                "status": child.status,
            }
            for child in sorted(category.children, key=lambda item: item.name)
            if child.status == "active"
        ],
        "updated_at": category.updated_at,
    }
    if include_sections:
        payload["sections"] = [
            _section_payload(item, db) for item in sorted(category.sections, key=lambda item: item.id)
        ]
    return payload


@router.get("/dashboard")
def dashboard(db: Db, actor: ReadActor):
    category_count = db.scalar(select(func.count()).select_from(Category)) or 0
    source_count = db.scalar(select(func.count()).select_from(SourceMaterial)) or 0
    return {
        "category_count": category_count,
        "source_count": source_count,
    }


def _search_snippet(text: str, query: str, width: int = 180) -> str:
    normalized = text or ""
    index = normalized.lower().find(query.lower())
    if index < 0:
        return normalized[:width]
    start = max(0, index - 60)
    end = min(len(normalized), index + len(query) + 120)
    prefix = "…" if start else ""
    suffix = "…" if end < len(normalized) else ""
    return f"{prefix}{normalized[start:end]}{suffix}"


@router.get("/search")
def search(
    q: str = Query(min_length=1, max_length=120),
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
    limit: int = Query(default=30, ge=1, le=100),
):
    del actor
    keyword = q.strip()
    if not keyword:
        return {"items": []}
    items: list[dict] = []
    categories = db.scalars(select(Category).order_by(Category.name).limit(300)).all()
    for category in categories:
        values = [category.name, category.code, category.description, *(category.aliases or [])]
        if any(keyword.lower() in str(value).lower() for value in values):
            items.append(
                {
                    "kind": "category",
                    "category_code": category.code,
                    "title": category.name,
                    "snippet": category.description,
                    "section_key": None,
                }
            )
    section_rows = db.execute(
        select(EncyclopediaSection, Category)
        .join(Category, Category.id == EncyclopediaSection.category_id)
        .where(EncyclopediaSection.content.contains(keyword))
        .order_by(EncyclopediaSection.updated_at.desc())
        .limit(limit)
    ).all()
    for section, category in section_rows:
        items.append(
            {
                "kind": "section",
                "category_code": category.code,
                "title": f"{category.name} · {section.title}",
                "snippet": _search_snippet(section.content, keyword),
                "section_key": section.section_key,
            }
        )
    # 搜索热点链接
    hotlink_rows = db.execute(
        select(HotLink, Category)
        .join(Category, Category.id == HotLink.category_id)
        .where(
            or_(
                HotLink.title.contains(keyword),
                HotLink.title_zh.contains(keyword),
                HotLink.description.contains(keyword),
                HotLink.description_zh.contains(keyword),
                HotLink.url.contains(keyword),
            )
        )
        .order_by(HotLink.collected_at.desc())
        .limit(limit)
    ).all()
    for link, category in hotlink_rows:
        display_title = link.title_zh or link.title
        display_description = link.description_zh or link.description
        items.append(
            {
                "kind": "hotlink",
                "category_code": category.code,
                "title": f"🔗 {display_title}",
                "snippet": f"{link.platform} · {display_description[:100]}" if display_description else link.platform,
                "section_key": "market",
            }
        )
    # 搜索趋势信号关键词
    trend_rows = db.execute(
        select(TrendSignal, Category)
        .join(Category, Category.id == TrendSignal.category_id)
        .where(
            or_(
                TrendSignal.keyword.contains(keyword),
                TrendSignal.title.contains(keyword),
                TrendSignal.title_zh.contains(keyword),
                TrendSignal.summary.contains(keyword),
                TrendSignal.summary_zh.contains(keyword),
            )
        )
        .order_by(TrendSignal.collected_at.desc())
        .limit(limit)
    ).all()
    for signal, category in trend_rows:
        display_title = signal.title_zh or signal.title or signal.keyword
        display_summary = signal.summary_zh or signal.summary
        items.append(
            {
                "kind": "trend",
                "category_code": category.code,
                "title": f"📊 {display_title}",
                "snippet": f"{signal.platform} · {display_summary[:100]}" if display_summary else signal.platform,
                "section_key": "market",
            }
        )
    source_rows = db.execute(
        select(SourceMaterial, Category)
        .join(Category, Category.id == SourceMaterial.category_id)
        .where(or_(SourceMaterial.title.contains(keyword), SourceMaterial.content.contains(keyword)))
        .order_by(SourceMaterial.collected_at.desc())
        .limit(limit)
    ).all()
    for source, category in source_rows:
        items.append(
            {
                "kind": "source",
                "category_code": category.code,
                "title": source.title,
                "snippet": _search_snippet(source.content or source.url or "", keyword),
                "section_key": "sources",
            }
        )
    return {"items": items[:limit]}


@router.get("/categories")
def categories(db: Db, actor: ReadActor, q: str | None = Query(default=None, max_length=100)):
    statement = select(Category).options(
        selectinload(Category.children), selectinload(Category.parent)
    # active=可进入百科；group=仅导航分组（如药物管理），不下钻独立百科页
    ).where(Category.status.in_(("active", "group")))
    if q:
        statement = statement.where(
            or_(Category.name.contains(q), Category.code.contains(q), Category.description.contains(q))
        )
    rows = db.scalars(statement.order_by(Category.parent_id, Category.name)).unique().all()
    return {"items": [_category_payload(item) for item in rows]}


@router.get("/categories/{code}")
def category_detail(code: str, db: Db, actor: ReadActor):
    category = _category_or_404(db, code)
    source_count = (
        db.scalar(
            select(func.count())
            .select_from(SourceMaterial)
            .where(SourceMaterial.category_id == category.id)
        )
        or 0
    )
    payload = _category_payload(category, include_sections=True, db=db)
    payload.update({"source_count": source_count})
    return payload


@router.patch("/categories/{code}")
def update_category(code: str, body: CategoryUpdate, db: Db, actor: WriteActor):
    ensure_role(actor, "admin", "researcher")
    category = _category_or_404(db, code)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return _category_payload(category, include_sections=True, db=db)


# ---------------------------------------------------------------------------
# Trend Signals (趋势信号 — 每日爬取的结构化数据)
# ---------------------------------------------------------------------------

@router.post("/trend-signals")
def create_trend_signal(body: TrendSignalCreate, db: Db, actor: WriteActor):
    ensure_role(actor, "admin", "data", "researcher")
    category = _category_or_404(db, body.category_code)
    signal = TrendSignal(
        category_id=category.id,
        section_key=body.section_key,
        signal_type=body.signal_type,
        platform=body.platform,
        keyword=body.keyword,
        title=body.title,
        title_zh=body.title_zh,
        metric_value=body.metric_value,
        metric_unit=body.metric_unit,
        trend_direction=body.trend_direction,
        summary=body.summary,
        summary_zh=body.summary_zh,
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return {"id": signal.id, "category_code": body.category_code}


@router.post("/trend-signals/batch")
def create_trend_signals_batch(body: TrendSignalBatch, db: Db, actor: WriteActor):
    ensure_role(actor, "admin", "data", "researcher")
    inserted: list[int] = []
    updated: list[int] = []
    skipped: list[str] = []
    category_codes = {item.category_code for item in body.items}
    categories = {
        category.code: category
        for category in db.scalars(
            select(Category).where(Category.code.in_(category_codes))
        )
    }
    for item in body.items:
        category = categories.get(item.category_code)
        if category is None:
            skipped.append(f"Category not found: {item.category_code}")
            continue
        signal = db.scalars(
            select(TrendSignal)
            .where(
                TrendSignal.category_id == category.id,
                TrendSignal.platform == item.platform,
                TrendSignal.title == item.title,
            )
            .limit(1)
        ).first()
        if signal is None:
            signal = TrendSignal(category_id=category.id)
            db.add(signal)
            is_new = True
        else:
            is_new = False
        signal.section_key = item.section_key
        signal.signal_type = item.signal_type
        signal.platform = item.platform
        signal.keyword = item.keyword
        signal.title = item.title
        signal.title_zh = item.title_zh
        signal.metric_value = item.metric_value
        signal.metric_unit = item.metric_unit
        signal.trend_direction = item.trend_direction
        signal.summary = item.summary
        signal.summary_zh = item.summary_zh
        signal.collected_at = datetime.now(UTC)
        db.flush()
        (inserted if is_new else updated).append(signal.id)
    db.commit()
    return {
        "inserted_count": len(inserted),
        "inserted_ids": inserted,
        "updated_count": len(updated),
        "updated_ids": updated,
        "skipped": skipped,
    }


@router.get("/categories/{code}/trend-signals")
def list_trend_signals(
    code: str,
    db: Db,
    actor: ReadActor,
    section_key: str | None = Query(default=None, max_length=80),
    platform: str | None = Query(default=None, max_length=40),
    days: int = Query(default=30, ge=1, le=365),
):
    category = _category_or_404(db, code)
    cutoff = datetime.now(UTC).replace(hour=0, minute=0, second=0)
    cutoff = cutoff - timedelta(days=days)
    filters = [TrendSignal.category_id == category.id, TrendSignal.collected_at >= cutoff]
    if section_key:
        filters.append(TrendSignal.section_key == section_key)
    if platform:
        filters.append(TrendSignal.platform == platform)
    rows = db.scalars(
        select(TrendSignal)
        .where(*filters)
        .order_by(TrendSignal.collected_at.desc(), TrendSignal.metric_value.desc())
        .limit(200)
    ).all()
    return {
        "items": [
            {
                "id": item.id,
                "category_code": category.code,
                "section_key": item.section_key,
                "signal_type": item.signal_type,
                "platform": item.platform,
                "keyword": item.keyword,
                "title": item.title,
                "title_zh": item.title_zh,
                "metric_value": item.metric_value,
                "metric_unit": item.metric_unit,
                "trend_direction": item.trend_direction,
                "summary": item.summary,
                "summary_zh": item.summary_zh,
                "collected_at": item.collected_at,
            }
            for item in rows
        ],
    }


# ---------------------------------------------------------------------------
# Hot Links (热点跳转链接 — 爆品/讨论/视频的结构化跳转)
# ---------------------------------------------------------------------------

@router.post("/hot-links")
def create_hot_link(body: HotLinkCreate, db: Db, actor: WriteActor):
    ensure_role(actor, "admin", "data", "researcher")
    category = _category_or_404(db, body.category_code)
    link = HotLink(
        category_id=category.id,
        section_key=body.section_key,
        link_type=body.link_type,
        platform=body.platform,
        title=body.title,
        title_zh=body.title_zh,
        url=str(body.url),
        description=body.description,
        description_zh=body.description_zh,
        hotness_score=body.hotness_score,
        is_hot=body.is_hot,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return {"id": link.id, "category_code": body.category_code, "url": str(body.url)}


@router.post("/hot-links/batch")
def create_hot_links_batch(body: HotLinkBatch, db: Db, actor: WriteActor):
    ensure_role(actor, "admin", "data", "researcher")
    inserted: list[int] = []
    updated: list[int] = []
    skipped: list[str] = []
    category_codes = {item.category_code for item in body.items}
    categories = {
        category.code: category
        for category in db.scalars(
            select(Category).where(Category.code.in_(category_codes))
        )
    }
    for item in body.items:
        category = categories.get(item.category_code)
        if category is None:
            skipped.append(f"Category not found: {item.category_code}")
            continue
        url = str(item.url)
        link = db.scalars(
            select(HotLink)
            .where(
                HotLink.category_id == category.id,
                HotLink.platform == item.platform,
                HotLink.url == url,
            )
            .limit(1)
        ).first()
        if link is None:
            link = HotLink(category_id=category.id)
            db.add(link)
            is_new = True
        else:
            is_new = False
        link.section_key = item.section_key
        link.link_type = item.link_type
        link.platform = item.platform
        link.title = item.title
        link.title_zh = item.title_zh
        link.url = url
        link.description = item.description
        link.description_zh = item.description_zh
        link.hotness_score = item.hotness_score
        link.is_hot = item.is_hot
        link.collected_at = datetime.now(UTC)
        db.flush()
        (inserted if is_new else updated).append(link.id)
    db.commit()
    return {
        "inserted_count": len(inserted),
        "inserted_ids": inserted,
        "updated_count": len(updated),
        "updated_ids": updated,
        "skipped": skipped,
    }


@router.get("/categories/{code}/hot-links")
def list_hot_links(
    code: str,
    db: Db,
    actor: ReadActor,
    section_key: str | None = Query(default=None, max_length=80),
    platform: str | None = Query(default=None, max_length=40),
    only_hot: bool = Query(default=False),
    days: int = Query(default=30, ge=1, le=365),
):
    category = _category_or_404(db, code)
    cutoff = datetime.now(UTC).replace(hour=0, minute=0, second=0) - timedelta(days=days)
    filters = [HotLink.category_id == category.id, HotLink.collected_at >= cutoff]
    if section_key:
        filters.append(HotLink.section_key == section_key)
    if platform:
        filters.append(HotLink.platform == platform)
    if only_hot:
        filters.append(HotLink.is_hot.is_(True))
    rows = db.scalars(
        select(HotLink)
        .where(*filters)
        .order_by(HotLink.is_hot.desc(), HotLink.hotness_score.desc(), HotLink.collected_at.desc())
        .limit(200)
    ).all()
    return {
        "items": [
            {
                "id": item.id,
                "category_code": category.code,
                "section_key": item.section_key,
                "link_type": item.link_type,
                "platform": item.platform,
                "title": item.title,
                "title_zh": item.title_zh,
                "url": item.url,
                "description": item.description,
                "description_zh": item.description_zh,
                "hotness_score": item.hotness_score,
                "is_hot": item.is_hot,
                "collected_at": item.collected_at,
            }
            for item in rows
        ],
    }


@router.delete("/hot-links/{link_id}")
def delete_hot_link(link_id: int, db: Db, actor: WriteActor):
    ensure_role(actor, "admin", "data")
    link = db.get(HotLink, link_id)
    if link is None:
        raise HTTPException(status_code=404, detail="Hot link not found")
    db.delete(link)
    db.commit()
    return {"ok": True}


@router.post("/hot-links/{link_id}/listing-suggestion-preview")
def generate_hot_link_listing_suggestion(
    link_id: int,
    db: Db,
    actor: WriteActor,
):
    """基于跨平台品类洞察生成非持久化 Listing 优化建议预览。"""
    ensure_role(actor, "admin", "data", "researcher")
    product = db.get(HotLink, link_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Hot link not found")
    try:
        return generate_listing_suggestion_preview(db, product=product)
    except ContentError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AgentError as exc:
        status_code = 503 if "API_KEY未配置" in str(exc) else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.delete("/categories/{code}/trend-signals")
def clear_trend_signals(
    code: str,
    db: Db,
    actor: WriteActor,
    platform: Annotated[str | None, Query(max_length=40)] = None,
):
    """删除某品类指定平台的旧趋势信号；未传平台时保持全量清理。"""
    ensure_role(actor, "admin", "data")
    category = _category_or_404(db, code)
    filters = [TrendSignal.category_id == category.id]
    if platform:
        filters.append(TrendSignal.platform == platform)
    rows = db.scalars(
        select(TrendSignal).where(*filters)
    ).all()
    count = len(rows)
    for row in rows:
        db.delete(row)
    db.commit()
    return {"ok": True, "deleted": count}


@router.post("/categories/{code}/crawl")
def trigger_crawl(code: str, db: Db, actor: WriteActor):
    """手动触发热点爬取 — 调用 hot-topic-crawler skill 的脚本。
    
    执行 run_full_crawl.py（YouTube + Bing News + Google Suggest），
    然后执行 crawl_reddit_single.py（当前品类的 Reddit 讨论帖）。
    """
    ensure_role(actor, "admin", "data", "researcher")
    settings = get_settings()
    if not settings.crawler_enabled:
        raise HTTPException(status_code=503, detail="暂未开放，请联系管理员")
    if not settings.crawler_scripts_dir:
        raise HTTPException(status_code=503, detail="爬虫脚本目录尚未配置")
    category = _category_or_404(db, code)
    import os
    import subprocess

    scripts_dir = os.path.expanduser(settings.crawler_scripts_dir)
    runner = os.path.join(scripts_dir, "run_full_crawl.py")
    reddit_runner = os.path.join(scripts_dir, "crawl_reddit_single.py")
    if not os.path.exists(runner):
        raise HTTPException(status_code=404, detail="Crawler script not found")

    env = os.environ.copy()
    env["ENCYCLOPEDIA_API_BASE"] = settings.crawler_api_base
    env["CRAWLER_USERNAME"] = env.get("CRAWLER_USERNAME", "admin")
    if settings.crawler_http_proxy:
        env["HTTP_PROXY"] = settings.crawler_http_proxy
    if settings.crawler_https_proxy:
        env["HTTPS_PROXY"] = settings.crawler_https_proxy
    # Read password from .crawler_password file or AUTH_USERS_JSON
    pass_file = os.path.expanduser(settings.crawler_password_file)
    if os.path.exists(pass_file):
        with open(pass_file) as f:
            env["CRAWLER_PASSWORD"] = f.read().strip()
    elif env.get("AUTH_USERS_JSON"):
        import json
        try:
            users = json.loads(env["AUTH_USERS_JSON"])
            for u in users:
                if u.get("username") == "admin":
                    env["CRAWLER_PASSWORD"] = u.get("password", "")
                    break
        except Exception:
            pass

    results = []

    # Step 1: Run full crawl (YouTube + Bing News + Google Suggest)
    try:
        result = subprocess.run(
            ["python3", runner],
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )
        results.append({
            "step": "full_crawl",
            "returncode": result.returncode,
            "stdout": result.stdout[-2000:],
            "stderr": result.stderr[-500:],
        })
    except subprocess.TimeoutExpired:
        results.append({"step": "full_crawl", "error": "timed out (5 min)"})
    except Exception as exc:
        results.append({"step": "full_crawl", "error": str(exc)})

    # Step 2: Run Reddit crawl for this category
    if os.path.exists(reddit_runner) and env.get("CRAWLER_PASSWORD"):
        try:
            result = subprocess.run(
                ["python3", reddit_runner, code],
                capture_output=True,
                text=True,
                timeout=180,
                env=env,
            )
            results.append({
                "step": "reddit_crawl",
                "returncode": result.returncode,
                "stdout": result.stdout[-1500:],
                "stderr": result.stderr[-500:],
            })
        except subprocess.TimeoutExpired:
            results.append({"step": "reddit_crawl", "error": "timed out (3 min)"})
        except Exception as exc:
            results.append({"step": "reddit_crawl", "error": str(exc)})

    return {"category": code, "results": results}


@router.post("/source-materials")
def add_source_material(body: SourceMaterialCreate, db: Db, actor: WriteActor):
    ensure_role(actor, "admin", "researcher")
    category = _category_or_404(db, body.category_code)
    material = SourceMaterial(
        category_id=category.id,
        source_type=body.source_type,
        title=body.title,
        url=str(body.url) if body.url else None,
        content=body.content,
        published_at=body.published_at,
        collected_at=body.collected_at or datetime.now(UTC),
        created_by=actor.name,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return {"id": material.id, "title": material.title, "source_type": material.source_type}


@router.get("/categories/{code}/source-materials")
def list_source_materials(code: str, db: Db, actor: ReadActor):
    category = _category_or_404(db, code)
    rows = db.scalars(
        select(SourceMaterial)
        .where(SourceMaterial.category_id == category.id)
        .order_by(SourceMaterial.id.desc())
    ).all()
    return {
        "items": [
            {
                "id": item.id,
                "source_type": item.source_type,
                "title": item.title,
                "url": item.url,
                "content": item.content,
                "published_at": item.published_at,
                "collected_at": item.collected_at,
                "created_by": item.created_by,
            }
            for item in rows
        ]
    }


@router.put("/categories/{code}/sections/{section_key}")
def update_section(
    code: str, section_key: str, body: SectionUpdate, db: Db, actor: WriteActor
):
    ensure_role(actor, "admin", "researcher")
    category = _category_or_404(db, code)
    try:
        section = save_section(
            db,
            category=category,
            section_key=section_key,
            content=body.content,
            generation_mode=body.generation_mode,
            actor=actor.name,
            evidence_source_ids=body.evidence_source_ids,
        )
        section = db.scalar(
            select(EncyclopediaSection)
            .options(selectinload(EncyclopediaSection.evidence))
            .where(EncyclopediaSection.id == section.id)
        )
        return _section_payload(section, db)
    except ContentError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/categories/{code}/generate-section")
def generate_category_section(code: str, db: Db, actor: WriteActor):
    """基于当前热点与趋势信号生成 06 章节摘要，并保留原始正文。"""
    ensure_role(actor, "admin", "researcher")
    category = _category_or_404(db, code)
    try:
        section = generate_market_brief(
            db,
            category=category,
            actor=actor.name,
        )
        section = db.scalar(
            select(EncyclopediaSection)
            .options(selectinload(EncyclopediaSection.evidence))
            .where(EncyclopediaSection.id == section.id)
        )
        return _section_payload(section, db)
    except ContentError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AgentError as exc:
        status_code = 503 if "API_KEY未配置" in str(exc) else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# 选品Agent
# ---------------------------------------------------------------------------

def _discovery_payload(d: ProductDiscovery) -> dict:
    return {
        "id": d.id,
        "scan_id": d.scan_id,
        "product_name": d.product_name,
        "category_code": d.category_code,
        "opportunity_type": d.opportunity_type,
        "opportunity_score": d.opportunity_score,
        "reasoning": d.reasoning,
        "market_signals": d.market_signals,
        "keywords": d.keywords,
        "source_links": d.source_links,
        "status": d.status,
        "user_note": d.user_note,
        "created_at": d.created_at,
    }


def _scan_payload(scan: AgentScan, *, include_details: bool = False, db: Session | None = None) -> dict:
    payload = {
        "id": scan.id,
        "scan_type": scan.scan_type,
        "category_code": scan.category_code,
        "topic": scan.topic,
        "status": scan.status,
        "triggered_by": scan.triggered_by,
        "is_pinned": bool(scan.is_pinned),
        "report": scan.report,
        "stats": scan.stats,
        "error_message": scan.error_message,
        "created_at": scan.created_at,
        "completed_at": scan.completed_at,
    }
    if include_details and db is not None:
        discoveries = db.scalars(
            select(ProductDiscovery).where(ProductDiscovery.scan_id == scan.id)
            .order_by(ProductDiscovery.opportunity_score.desc())
        ).all()
        payload["discoveries"] = [_discovery_payload(d) for d in discoveries]
        messages = db.scalars(
            select(AgentMessage).where(AgentMessage.scan_id == scan.id)
            .order_by(AgentMessage.id)
        ).all()
        payload["messages"] = [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at,
            }
            for m in messages
        ]
    return payload


@router.post("/agent/scan")
def trigger_agent_scan(body: AgentScanRequest, db: Db, actor: WriteActor):
    """触发选品Agent扫描。"""
    ensure_role(actor, "admin", "data", "researcher")
    if body.category_code and db.scalar(select(Category.id).where(Category.code == body.category_code)) is None:
        raise HTTPException(status_code=404, detail="Category not found")
    try:
        scan = run_scan(
            db,
            scan_type=body.scan_type,
            category_code=body.category_code,
            topic=body.topic,
            actor=actor.name,
        )
        return _scan_payload(scan, include_details=True, db=db)
    except AgentError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/agent/scans")
def list_agent_scans(db: Db, actor: ReadActor, limit: int = Query(default=20, ge=1, le=100)):
    """列出选品Agent扫描历史。"""
    rows = db.scalars(
        select(AgentScan)
        .order_by(AgentScan.is_pinned.desc(), AgentScan.id.desc())
        .limit(limit)
    ).all()
    return {"items": [_scan_payload(s) for s in rows]}


@router.get("/agent/scans/{scan_id}")
def agent_scan_detail(scan_id: int, db: Db, actor: ReadActor):
    """获取扫描详情（含discoveries和messages）。"""
    scan = db.get(AgentScan, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return _scan_payload(scan, include_details=True, db=db)


@router.patch("/agent/scans/{scan_id}")
def update_agent_scan(scan_id: int, body: AgentScanUpdateRequest, db: Db, actor: WriteActor):
    """更新扫描会话（目前支持顶置）。"""
    ensure_role(actor, "admin", "data", "researcher")
    scan = db.get(AgentScan, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    scan.is_pinned = body.is_pinned
    db.commit()
    db.refresh(scan)
    return _scan_payload(scan)


@router.delete("/agent/scans/{scan_id}")
def delete_agent_scan(scan_id: int, db: Db, actor: WriteActor):
    """硬删除扫描会话及其 discoveries / messages。"""
    ensure_role(actor, "admin", "data", "researcher")
    scan = db.get(AgentScan, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    db.delete(scan)
    db.commit()
    return {"ok": True, "deleted": scan_id}


@router.post("/agent/scans/{scan_id}/chat")
def agent_scan_chat(scan_id: int, body: AgentChatRequest, db: Db, actor: WriteActor):
    """在扫描会话中进行多轮对话。"""
    ensure_role(actor, "admin", "data", "researcher")
    try:
        result = agent_chat(db, scan_id, body.message)
        return {"content": result["content"], "usage": result.get("usage", {})}
    except AgentError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/agent/scans/{scan_id}/chat/stream")
def agent_scan_chat_stream(scan_id: int, body: AgentChatRequest, actor: WriteActor):
    """流式多轮对话（SSE）。不长期持有 DB 连接。"""
    ensure_role(actor, "admin", "data", "researcher")

    def generate() -> Iterator[str]:
        try:
            for event in agent_chat_stream(scan_id, body.message):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:  # noqa: BLE001 — SSE 内兜底，避免连接悬挂
            payload = {"event": "error", "data": {"message": str(exc)[:240]}}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/agent/scans/{scan_id}/discoveries")
def list_discoveries(scan_id: int, db: Db, actor: ReadActor):
    """获取某次扫描发现的产品/机会点。"""
    scan = db.get(AgentScan, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    rows = db.scalars(
        select(ProductDiscovery).where(ProductDiscovery.scan_id == scan_id)
        .order_by(ProductDiscovery.opportunity_score.desc())
    ).all()
    return {"items": [_discovery_payload(d) for d in rows]}


@router.patch("/agent/discoveries/{discovery_id}")
def update_discovery(discovery_id: int, body: DiscoveryUpdateRequest, db: Db, actor: WriteActor):
    """更新发现状态或添加备注。"""
    ensure_role(actor, "admin", "data", "researcher")
    discovery = db.get(ProductDiscovery, discovery_id)
    if discovery is None:
        raise HTTPException(status_code=404, detail="Discovery not found")
    if body.status is not None:
        discovery.status = body.status
    if body.user_note is not None:
        discovery.user_note = body.user_note
    db.commit()
    db.refresh(discovery)
    return _discovery_payload(discovery)


@router.get("/agent/discoveries")
def all_discoveries(
    db: Db,
    actor: ReadActor,
    status: str | None = Query(default=None),
    opportunity_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    """跨扫描汇总查看所有发现。"""
    stmt = select(ProductDiscovery).order_by(ProductDiscovery.opportunity_score.desc()).limit(limit)
    filters = []
    if status:
        filters.append(ProductDiscovery.status == status)
    if opportunity_type:
        filters.append(ProductDiscovery.opportunity_type == opportunity_type)
    if filters:
        stmt = stmt.where(*filters)
    rows = db.scalars(stmt).all()
    return {"items": [_discovery_payload(d) for d in rows]}
