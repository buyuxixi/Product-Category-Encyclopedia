from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
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
    Category,
    EncyclopediaSection,
    EncyclopediaVersion,
    HotLink,
    ImportJob,
    ListingSnapshot,
    PublicationRecord,
    SourceMaterial,
    TrendSignal,
)
from app.schemas import (
    AmazonImportRequest,
    CategoryUpdate,
    DraftRequest,
    HotLinkBatch,
    HotLinkCreate,
    LocalLoginRequest,
    PublishRequest,
    ReviewRequest,
    SectionUpdate,
    SourceMaterialCreate,
    SubmitReviewRequest,
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
from app.services.draft_service import generate_draft
from app.services.import_service import (
    ImportValidationError,
    import_amazon_directories,
    list_import_catalog,
)
from app.services.workflow_service import (
    WorkflowError,
    publish_version,
    render_version_markdown,
    review_version,
    save_section,
    submit_for_review,
)


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
        "feishu_publish_enabled": bool(settings.feishu_app_id and settings.feishu_app_secret),
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
        if db is not None and evidence.source_type == "listing_snapshot":
            listing = db.get(ListingSnapshot, evidence.source_id)
            if listing is not None:
                item["source"] = {
                    "title": listing.title,
                    "asin": listing.asin,
                    "brand": listing.brand,
                    "marketplace": listing.marketplace,
                    "scraped_at": listing.scraped_at,
                    "url": listing.source_url,
                }
        elif db is not None and evidence.source_type == "source_material":
            source = db.get(SourceMaterial, evidence.source_id)
            if source is not None:
                item["source"] = {
                    "title": source.title,
                    "source_type": source.source_type,
                    "collected_at": source.collected_at,
                    "published_at": source.published_at,
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
        "review_status": section.review_status,
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
        "workflow_status": category.workflow_status,
        "parent_code": category.parent.code if category.parent else None,
        "children": [
            {
                "id": child.id,
                "code": child.code,
                "name": child.name,
                "workflow_status": child.workflow_status,
            }
            for child in sorted(category.children, key=lambda item: item.name)
        ],
        "updated_at": category.updated_at,
    }
    if include_sections:
        payload["sections"] = [
            _section_payload(item, db) for item in sorted(category.sections, key=lambda item: item.id)
        ]
    return payload


def _job_payload(job: ImportJob) -> dict:
    return {
        "id": job.id,
        "status": job.status,
        "source_path": Path(job.source_path).name or "configured import root",
        "requested_directories": job.requested_directories,
        "total_count": job.total_count,
        "inserted_count": job.inserted_count,
        "duplicate_count": job.duplicate_count,
        "failed_count": job.failed_count,
        "skipped_count": job.skipped_count,
        "errors": job.errors,
        "created_by": job.created_by,
        "created_at": job.created_at,
    }


def _version_payload(version: EncyclopediaVersion) -> dict:
    return {
        "id": version.id,
        "category_id": version.category_id,
        "category_code": version.category.code if version.category else None,
        "category_name": version.category.name if version.category else None,
        "version_number": version.version_number,
        "status": version.status,
        "created_by": version.created_by,
        "reviewed_by": version.reviewed_by,
        "review_comment": version.review_comment,
        "created_at": version.created_at,
        "reviewed_at": version.reviewed_at,
        "published_at": version.published_at,
    }


@router.get("/dashboard")
def dashboard(db: Db, actor: ReadActor):
    category_count = db.scalar(select(func.count()).select_from(Category)) or 0
    listing_count = db.scalar(select(func.count()).select_from(ListingSnapshot)) or 0
    source_count = db.scalar(select(func.count()).select_from(SourceMaterial)) or 0
    pending_count = (
        db.scalar(
            select(func.count())
            .select_from(EncyclopediaVersion)
            .where(EncyclopediaVersion.status == "pending_review")
        )
        or 0
    )
    recent_imports = db.scalars(select(ImportJob).order_by(ImportJob.id.desc()).limit(5)).all()
    return {
        "category_count": category_count,
        "listing_count": listing_count,
        "source_count": source_count,
        "pending_review_count": pending_count,
        "recent_imports": [_job_payload(item) for item in recent_imports],
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
    listing_rows = db.execute(
        select(ListingSnapshot, Category)
        .join(Category, Category.id == ListingSnapshot.category_id)
        .where(
            or_(
                ListingSnapshot.asin.contains(keyword),
                ListingSnapshot.title.contains(keyword),
                ListingSnapshot.brand.contains(keyword),
            )
        )
        .order_by(ListingSnapshot.scraped_at.desc())
        .limit(limit)
    ).all()
    for listing, category in listing_rows:
        items.append(
            {
                "kind": "listing",
                "category_code": category.code,
                "title": listing.title or listing.asin,
                "snippet": f"{listing.brand} · {listing.asin} · {listing.marketplace}",
                "section_key": "amazon_insights",
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
    )
    if q:
        statement = statement.where(
            or_(Category.name.contains(q), Category.code.contains(q), Category.description.contains(q))
        )
    rows = db.scalars(statement.order_by(Category.parent_id, Category.name)).unique().all()
    return {"items": [_category_payload(item) for item in rows]}


@router.get("/categories/{code}")
def category_detail(code: str, db: Db, actor: ReadActor):
    category = _category_or_404(db, code)
    listing_count = (
        db.scalar(
            select(func.count())
            .select_from(ListingSnapshot)
            .where(ListingSnapshot.category_id == category.id)
        )
        or 0
    )
    source_count = (
        db.scalar(
            select(func.count())
            .select_from(SourceMaterial)
            .where(SourceMaterial.category_id == category.id)
        )
        or 0
    )
    payload = _category_payload(category, include_sections=True, db=db)
    payload.update({"listing_count": listing_count, "source_count": source_count})
    return payload


@router.patch("/categories/{code}")
def update_category(code: str, body: CategoryUpdate, db: Db, actor: WriteActor):
    ensure_role(actor, "admin", "researcher")
    category = _category_or_404(db, code)
    if category.workflow_status in {"pending_review", "approved", "published"}:
        raise HTTPException(status_code=409, detail="当前版本已锁定，请先创建新的草稿版本")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    category.workflow_status = "draft"
    db.commit()
    db.refresh(category)
    return _category_payload(category, include_sections=True, db=db)


@router.get("/categories/{code}/listings")
def category_listings(
    code: str,
    db: Db,
    actor: ReadActor,
    q: str | None = Query(default=None, max_length=200),
    brand: str | None = Query(default=None, max_length=255),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    category = _category_or_404(db, code)
    filters = [ListingSnapshot.category_id == category.id]
    if q:
        filters.append(
            or_(
                ListingSnapshot.asin.contains(q),
                ListingSnapshot.title.contains(q),
                ListingSnapshot.brand.contains(q),
            )
        )
    if brand:
        filters.append(ListingSnapshot.brand == brand)
    total = db.scalar(select(func.count()).select_from(ListingSnapshot).where(*filters)) or 0
    rows = db.scalars(
        select(ListingSnapshot)
        .where(*filters)
        .order_by(ListingSnapshot.bsr_rank.is_(None), ListingSnapshot.bsr_rank, ListingSnapshot.asin)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": item.id,
                "asin": item.asin,
                "title": item.title,
                "brand": item.brand,
                "rating_value": item.rating_value,
                "rating_count": item.rating_count,
                "current_price": item.current_price,
                "currency": item.currency,
                "bsr_rank": item.bsr_rank,
                "bsr_category": item.bsr_category,
                "scraped_at": item.scraped_at,
                "source_url": item.source_url,
            }
            for item in rows
        ],
    }


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
        metric_value=body.metric_value,
        metric_unit=body.metric_unit,
        trend_direction=body.trend_direction,
        summary=body.summary,
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return {"id": signal.id, "category_code": body.category_code}


@router.post("/trend-signals/batch")
def create_trend_signals_batch(body: TrendSignalBatch, db: Db, actor: WriteActor):
    ensure_role(actor, "admin", "data", "researcher")
    inserted: list[int] = []
    skipped: list[str] = []
    for item in body.items:
        category = db.scalar(select(Category).where(Category.code == item.category_code))
        if category is None:
            skipped.append(f"Category not found: {item.category_code}")
            continue
        signal = TrendSignal(
            category_id=category.id,
            section_key=item.section_key,
            signal_type=item.signal_type,
            platform=item.platform,
            keyword=item.keyword,
            title=item.title,
            metric_value=item.metric_value,
            metric_unit=item.metric_unit,
            trend_direction=item.trend_direction,
            summary=item.summary,
        )
        db.add(signal)
        db.flush()
        inserted.append(signal.id)
    db.commit()
    return {"inserted_count": len(inserted), "inserted_ids": inserted, "skipped": skipped}


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
                "section_key": item.section_key,
                "signal_type": item.signal_type,
                "platform": item.platform,
                "keyword": item.keyword,
                "title": item.title,
                "metric_value": item.metric_value,
                "metric_unit": item.metric_unit,
                "trend_direction": item.trend_direction,
                "summary": item.summary,
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
        url=str(body.url),
        description=body.description,
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
    skipped: list[str] = []
    for item in body.items:
        category = db.scalar(select(Category).where(Category.code == item.category_code))
        if category is None:
            skipped.append(f"Category not found: {item.category_code}")
            continue
        link = HotLink(
            category_id=category.id,
            section_key=item.section_key,
            link_type=item.link_type,
            platform=item.platform,
            title=item.title,
            url=str(item.url),
            description=item.description,
            hotness_score=item.hotness_score,
            is_hot=item.is_hot,
        )
        db.add(link)
        db.flush()
        inserted.append(link.id)
    db.commit()
    return {"inserted_count": len(inserted), "inserted_ids": inserted, "skipped": skipped}


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
                "section_key": item.section_key,
                "link_type": item.link_type,
                "platform": item.platform,
                "title": item.title,
                "url": item.url,
                "description": item.description,
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


@router.post("/imports/amazon")
def import_amazon(body: AmazonImportRequest, db: Db, actor: WriteActor):
    ensure_role(actor, "admin", "data")
    try:
        job = import_amazon_directories(
            db,
            root_path=body.root_path,
            requested_directories=body.directories,
            actor=actor.name,
        )
        return _job_payload(job)
    except ImportValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/imports/catalog")
def import_catalog(
    db: Db,
    actor: ReadActor,
    root_path: str = Query(default="/imports", max_length=500),
):
    del db, actor
    try:
        return {"root_path": root_path, "items": list_import_catalog(root_path)}
    except ImportValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/imports")
def list_imports(db: Db, actor: ReadActor):
    rows = db.scalars(select(ImportJob).order_by(ImportJob.id.desc()).limit(50)).all()
    return {"items": [_job_payload(item) for item in rows]}


@router.get("/imports/{job_id}")
def import_detail(job_id: int, db: Db, actor: ReadActor):
    job = db.get(ImportJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Import job not found")
    return _job_payload(job)


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


@router.post("/categories/{code}/drafts")
def create_draft(code: str, body: DraftRequest, db: Db, actor: WriteActor):
    ensure_role(actor, "admin", "researcher")
    category = _category_or_404(db, code)
    try:
        return generate_draft(
            db,
            category,
            body.listing_limit,
            listing_ids=body.listing_ids,
            source_material_ids=body.source_material_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
            evidence_listing_ids=body.evidence_listing_ids,
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
    except WorkflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/categories/{code}/submit-review")
def submit_review(code: str, body: SubmitReviewRequest, db: Db, actor: WriteActor):
    ensure_role(actor, "admin", "researcher")
    category = _category_or_404(db, code)
    try:
        return _version_payload(
            submit_for_review(db, category=category, actor=actor.name, note=body.note)
        )
    except WorkflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/versions")
def list_versions(
    db: Db,
    actor: ReadActor,
    status: str | None = Query(default=None, max_length=32),
    category_code: str | None = Query(default=None, max_length=80),
):
    statement = select(EncyclopediaVersion).options(selectinload(EncyclopediaVersion.category))
    if status:
        statement = statement.where(EncyclopediaVersion.status == status)
    if category_code:
        statement = statement.join(Category).where(Category.code == category_code)
    rows = db.scalars(statement.order_by(EncyclopediaVersion.id.desc()).limit(100)).all()
    return {"items": [_version_payload(item) for item in rows]}


@router.get("/versions/{version_id}")
def version_detail(version_id: int, db: Db, actor: ReadActor):
    version = db.scalar(
        select(EncyclopediaVersion)
        .options(selectinload(EncyclopediaVersion.category))
        .where(EncyclopediaVersion.id == version_id)
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")
    payload = _version_payload(version)
    payload["content_snapshot"] = version.content_snapshot
    return payload


@router.get("/versions/{version_id}/diff")
def version_diff(version_id: int, db: Db, actor: ReadActor):
    version = db.get(EncyclopediaVersion, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")
    previous = db.scalar(
        select(EncyclopediaVersion)
        .where(
            EncyclopediaVersion.category_id == version.category_id,
            EncyclopediaVersion.version_number < version.version_number,
        )
        .order_by(EncyclopediaVersion.version_number.desc())
    )
    current_sections = {
        item["section_key"]: item for item in version.content_snapshot.get("sections", [])
    }
    previous_sections = (
        {item["section_key"]: item for item in previous.content_snapshot.get("sections", [])}
        if previous
        else {}
    )
    changes = []
    for section_key in sorted(set(current_sections) | set(previous_sections)):
        before = previous_sections.get(section_key, {}).get("content", "")
        after = current_sections.get(section_key, {}).get("content", "")
        if before == after:
            continue
        changes.append(
            {
                "section_key": section_key,
                "title": current_sections.get(section_key, previous_sections.get(section_key, {})).get(
                    "title", section_key
                ),
                "before": before,
                "after": after,
            }
        )
    return {
        "version_id": version.id,
        "previous_version_id": previous.id if previous else None,
        "changes": changes,
    }


@router.post("/versions/{version_id}/review")
def decide_review(version_id: int, body: ReviewRequest, db: Db, actor: WriteActor):
    ensure_role(actor, "admin", "reviewer")
    version = db.get(EncyclopediaVersion, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")
    try:
        return _version_payload(
            review_version(
                db,
                version=version,
                decision=body.decision,
                comment=body.comment,
                actor=actor.name,
            )
        )
    except WorkflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/versions/{version_id}/publication-preview")
def publication_preview(version_id: int, db: Db, actor: ReadActor):
    version = db.get(EncyclopediaVersion, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return {"version_id": version.id, "content": render_version_markdown(version)}


@router.post("/versions/{version_id}/publish")
def publish(version_id: int, body: PublishRequest, db: Db, actor: WriteActor):
    ensure_role(actor, "admin", "reviewer")
    version = db.get(EncyclopediaVersion, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")
    try:
        record = publish_version(
            db, version=version, provider_name=body.provider, actor=actor.name
        )
        return {
            "id": record.id,
            "status": record.status,
            "provider": record.provider,
            "external_doc_id": record.external_doc_id,
            "external_url": record.external_url,
            "error_message": record.error_message,
            "preview_content": record.preview_content,
        }
    except WorkflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/publications")
def list_publications(db: Db, actor: ReadActor):
    rows = db.scalars(select(PublicationRecord).order_by(PublicationRecord.id.desc()).limit(100)).all()
    return {
        "items": [
            {
                "id": item.id,
                "category_id": item.category_id,
                "version_id": item.version_id,
                "provider": item.provider,
                "status": item.status,
                "external_doc_id": item.external_doc_id,
                "external_url": item.external_url,
                "error_message": item.error_message,
                "created_at": item.created_at,
            }
            for item in rows
        ]
    }
