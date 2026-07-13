from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import AuditEvent, Category, EncyclopediaSection, EvidenceLink, SourceMaterial


class ContentError(ValueError):
    pass


def save_section(
    db: Session,
    *,
    category: Category,
    section_key: str,
    content: str,
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
        raise ContentError("Unknown encyclopedia section")
    if generation_mode == "generated" and section.locked_by_human and section.content.strip():
        raise ContentError("Human-edited section is locked; apply the suggestion manually")

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
        raise ContentError("Evidence sources must exist and belong to the selected category")

    section.content = content
    section.generation_mode = generation_mode
    section.locked_by_human = generation_mode == "human"
    section.updated_by = actor
    section.evidence.clear()
    for source_id in sorted(valid_source_ids):
        section.evidence.append(
            EvidenceLink(
                source_type="source_material",
                source_id=source_id,
                locator="Registered source material",
            )
        )

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
