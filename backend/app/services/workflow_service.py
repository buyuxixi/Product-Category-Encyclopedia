from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.integrations.feishu import get_publisher
from app.models import (
    AuditEvent,
    Category,
    EncyclopediaSection,
    EncyclopediaVersion,
    EvidenceLink,
    ListingSnapshot,
    PublicationRecord,
    SourceMaterial,
)


class WorkflowError(ValueError):
    pass


def _evidence_title(db: Session, source_type: str, source_id: int) -> str:
    if source_type == "listing_snapshot":
        listing = db.get(ListingSnapshot, source_id)
        return listing.title or listing.asin if listing else f"Listing #{source_id}"
    if source_type == "source_material":
        source = db.get(SourceMaterial, source_id)
        return source.title if source else f"Source #{source_id}"
    return f"{source_type} #{source_id}"


def _evidence_url(db: Session, source_type: str, source_id: int) -> str | None:
    if source_type == "listing_snapshot":
        listing = db.get(ListingSnapshot, source_id)
        return listing.source_url if listing else None
    if source_type == "source_material":
        source = db.get(SourceMaterial, source_id)
        return source.url if source else None
    return None


def save_section(
    db: Session,
    *,
    category: Category,
    section_key: str,
    content: str,
    evidence_listing_ids: list[int],
    generation_mode: str,
    actor: str,
    evidence_source_ids: list[int] | None = None,
) -> EncyclopediaSection:
    section = db.scalar(
        select(EncyclopediaSection)
        .options(selectinload(EncyclopediaSection.evidence))
        .where(
            EncyclopediaSection.category_id == category.id,
            EncyclopediaSection.section_key == section_key,
        )
    )
    if section is None:
        raise WorkflowError("Unknown encyclopedia section")
    if category.workflow_status in {"pending_review", "approved", "published"}:
        raise WorkflowError("当前版本已锁定，请先创建新的草稿版本")
    if generation_mode == "generated" and section.locked_by_human and section.content.strip():
        raise WorkflowError("Human-edited section is locked; apply the suggestion manually")

    requested_evidence_ids = set(evidence_listing_ids)
    valid_evidence_ids = set(
        db.scalars(
            select(ListingSnapshot.id).where(
                ListingSnapshot.category_id == category.id,
                ListingSnapshot.id.in_(requested_evidence_ids),
            )
        ).all()
    ) if requested_evidence_ids else set()
    if valid_evidence_ids != requested_evidence_ids:
        raise WorkflowError("Evidence listings must exist and belong to the selected category")
    requested_source_ids = set(evidence_source_ids or [])
    valid_source_ids = set(
        db.scalars(
            select(SourceMaterial.id).where(
                SourceMaterial.category_id == category.id,
                SourceMaterial.id.in_(requested_source_ids),
            )
        ).all()
    ) if requested_source_ids else set()
    if valid_source_ids != requested_source_ids:
        raise WorkflowError("Evidence sources must exist and belong to the selected category")

    section.content = content
    section.generation_mode = generation_mode
    section.locked_by_human = generation_mode == "human"
    section.review_status = "draft"
    section.updated_by = actor
    section.evidence.clear()
    for listing_id in sorted(valid_evidence_ids):
        section.evidence.append(
            EvidenceLink(
                source_type="listing_snapshot",
                source_id=listing_id,
                locator="Amazon Listing snapshot",
            )
        )
    for source_id in sorted(valid_source_ids):
        section.evidence.append(
            EvidenceLink(
                source_type="source_material",
                source_id=source_id,
                locator="Registered source material",
            )
        )
    category.workflow_status = "draft"
    db.add(
        AuditEvent(
            actor=actor,
            action="section_updated",
            entity_type="encyclopedia_section",
            entity_id=str(section.id),
            metadata_json={"section_key": section_key, "mode": generation_mode},
        )
    )
    db.commit()
    db.refresh(section)
    return section


def submit_for_review(db: Session, *, category: Category, actor: str, note: str | None):
    db.scalar(select(Category.id).where(Category.id == category.id).with_for_update())
    pending_version_id = db.scalar(
        select(EncyclopediaVersion.id).where(
            EncyclopediaVersion.category_id == category.id,
            EncyclopediaVersion.status == "pending_review",
        )
    )
    if pending_version_id is not None:
        raise WorkflowError("This category already has a version pending review")

    sections = db.scalars(
        select(EncyclopediaSection)
        .options(selectinload(EncyclopediaSection.evidence))
        .where(EncyclopediaSection.category_id == category.id)
        .order_by(EncyclopediaSection.id)
    ).all()
    if not any(section.content.strip() for section in sections):
        raise WorkflowError("At least one encyclopedia section must contain content")
    missing_evidence = [
        section.title
        for section in sections
        if not section.evidence
        and section.content.strip()
        and "暂无" not in section.content
        and "待验证" not in section.content
        and "待补充" not in section.content
    ]
    if missing_evidence:
        raise WorkflowError(f"以下模块缺少证据或待验证标记：{', '.join(missing_evidence[:3])}")
    next_number = (
        db.scalar(
            select(func.max(EncyclopediaVersion.version_number)).where(
                EncyclopediaVersion.category_id == category.id
            )
        )
        or 0
    ) + 1
    snapshot = {
        "category": {
            "code": category.code,
            "name": category.name,
            "description": category.description,
            "aliases": category.aliases,
            "included_items": category.included_items,
            "excluded_items": category.excluded_items,
        },
        "sections": [
            {
                "section_key": item.section_key,
                "title": item.title,
                "content": item.content or "暂无数据，待补充。",
                "evidence": [
                    {
                        "source_type": evidence.source_type,
                        "source_id": evidence.source_id,
                        "locator": evidence.locator,
                        "title": _evidence_title(db, evidence.source_type, evidence.source_id),
                        "url": _evidence_url(db, evidence.source_type, evidence.source_id),
                    }
                    for evidence in item.evidence
                ],
            }
            for item in sections
        ],
        "submission_note": note,
    }
    version = EncyclopediaVersion(
        category_id=category.id,
        version_number=next_number,
        status="pending_review",
        content_snapshot=snapshot,
        created_by=actor,
    )
    db.add(version)
    category.workflow_status = "pending_review"
    for section in sections:
        section.review_status = "pending_review"
    db.flush()
    db.add(
        AuditEvent(
            actor=actor,
            action="version_submitted",
            entity_type="encyclopedia_version",
            entity_id=str(version.id),
            metadata_json={"version_number": next_number},
        )
    )
    db.commit()
    db.refresh(version)
    return version


def review_version(
    db: Session, *, version: EncyclopediaVersion, decision: str, comment: str, actor: str
):
    if version.status != "pending_review":
        raise WorkflowError("Only pending versions can be reviewed")
    category = db.get(Category, version.category_id)
    if category is None:
        raise WorkflowError("Category no longer exists")
    version.reviewed_by = actor
    version.reviewed_at = datetime.now(UTC)
    version.review_comment = comment
    version.status = "approved" if decision == "approve" else "rejected"
    category.workflow_status = "approved" if decision == "approve" else "draft"
    sections = db.scalars(
        select(EncyclopediaSection).where(
            EncyclopediaSection.category_id == category.id,
            EncyclopediaSection.review_status == "pending_review",
        )
    ).all()
    for section in sections:
        section.review_status = "approved" if decision == "approve" else "draft"
    db.add(
        AuditEvent(
            actor=actor,
            action=f"version_{version.status}",
            entity_type="encyclopedia_version",
            entity_id=str(version.id),
            metadata_json={"comment_present": bool(comment)},
        )
    )
    db.commit()
    db.refresh(version)
    return version


def render_version_markdown(version: EncyclopediaVersion) -> str:
    snapshot = version.content_snapshot
    category = snapshot["category"]
    lines = [
        f"# {category['name']}品类百科",
        "",
        f"> 版本：v{version.version_number} | 状态：{version.status}",
        "",
    ]
    for section in snapshot.get("sections", []):
        lines.extend([f"## {section['title']}", "", section.get("content") or "暂无内容", ""])
        evidence_list = section.get("evidence", [])
        if evidence_list:
            lines.append("> 来源：")
            for ev in evidence_list:
                title = ev.get("title") or f"{ev.get('source_type')} #{ev.get('source_id')}"
                url = ev.get("url")
                if url:
                    lines.append(f"> - [{title}]({url})")
                else:
                    lines.append(f"> - {title}")
            lines.append("")
    lines.extend(["---", "", "本文由产品品类百科系统发布，Web 系统为唯一数据主库。"])
    return "\n".join(lines)


def publish_version(
    db: Session, *, version: EncyclopediaVersion, provider_name: str, actor: str
) -> PublicationRecord:
    if version.status not in {"approved", "published"}:
        raise WorkflowError("Only approved versions can be published")
    existing = db.scalar(
        select(PublicationRecord).where(
            PublicationRecord.provider == provider_name,
            PublicationRecord.version_id == version.id,
        )
    )
    if existing and existing.status == "published":
        return existing

    preview = render_version_markdown(version)
    record = existing or PublicationRecord(
        category_id=version.category_id,
        version_id=version.id,
        provider=provider_name,
        status="publishing",
        published_by=actor,
    )
    record.preview_content = preview
    record.status = "publishing"
    record.error_code = None
    record.error_message = None
    db.add(record)
    db.commit()
    db.refresh(record)

    try:
        result = get_publisher(provider_name).publish(
            version_id=version.id,
            title=f"{version.content_snapshot['category']['name']}品类百科",
            content=preview,
        )
        record.external_doc_id = result.external_doc_id
        record.external_url = result.external_url
        record.status = "published"
        version.status = "published"
        version.published_at = datetime.now(UTC)
        category = db.get(Category, version.category_id)
        if category:
            category.workflow_status = "published"
    except Exception as exc:
        record.status = "failed"
        record.error_code = "provider_error"
        record.error_message = str(exc)[:500]

    db.add(
        AuditEvent(
            actor=actor,
            action=f"publication_{record.status}",
            entity_type="publication_record",
            entity_id=str(record.id),
            metadata_json={"provider": provider_name, "version_id": version.id},
        )
    )
    db.commit()
    db.refresh(record)
    return record
