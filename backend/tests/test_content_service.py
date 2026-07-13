from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models import Category, EncyclopediaSection, EvidenceLink, SourceMaterial
from app.services.content_service import ContentError, save_section


def _category_with_section(db):
    category = db.scalar(select(Category).where(Category.parent_id.is_(None)))
    assert category is not None
    section = db.scalar(
        select(EncyclopediaSection).where(EncyclopediaSection.category_id == category.id)
    )
    assert section is not None
    return category, section


def _source(db, category_id: int, title: str) -> SourceMaterial:
    source = SourceMaterial(
        category_id=category_id,
        source_type="research",
        title=title,
        content="支持该章节的研究材料",
        created_by="tester",
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def test_save_section_binds_source_material_evidence(db):
    category, section = _category_with_section(db)
    source = _source(db, category.id, "研究来源")

    saved = save_section(
        db,
        category=category,
        section_key=section.section_key,
        content="更新后的章节内容",
        generation_mode="human",
        actor="tester",
        evidence_source_ids=[source.id],
    )

    assert saved.content == "更新后的章节内容"
    assert saved.locked_by_human is True
    evidence = db.scalars(
        select(EvidenceLink).where(EvidenceLink.section_id == section.id)
    ).all()
    assert [(item.source_type, item.source_id) for item in evidence] == [
        ("source_material", source.id)
    ]


def test_human_edit_cannot_be_overwritten_by_generated_content(db):
    category, section = _category_with_section(db)
    save_section(
        db,
        category=category,
        section_key=section.section_key,
        content="人工编辑内容",
        generation_mode="human",
        actor="tester",
    )

    with pytest.raises(ContentError, match="locked"):
        save_section(
            db,
            category=category,
            section_key=section.section_key,
            content="自动生成内容",
            generation_mode="generated",
            actor="agent",
        )


def test_evidence_source_must_belong_to_selected_category(db):
    category, section = _category_with_section(db)
    other = db.scalar(
        select(Category).where(Category.id != category.id, Category.parent_id.is_(None))
    )
    if other is None:
        pytest.skip("seed data has only one root category")
    source = _source(db, other.id, "其他品类来源")

    with pytest.raises(ContentError, match="belong to the selected category"):
        save_section(
            db,
            category=category,
            section_key=section.section_key,
            content="不应保存",
            generation_mode="human",
            actor="tester",
            evidence_source_ids=[source.id],
        )
