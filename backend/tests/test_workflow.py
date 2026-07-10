from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import select

from app.models import Category, EncyclopediaSection, ListingSnapshot
from app.services.draft_service import generate_draft
from app.services.workflow_service import (
    WorkflowError,
    publish_version,
    review_version,
    save_section,
    submit_for_review,
)


def category(db, code: str = "FAR_INFRARED") -> Category:
    return db.scalar(select(Category).where(Category.code == code))


def add_listing(db, target: Category):
    listing = ListingSnapshot(
        marketplace="US",
        asin="B012345678",
        category_id=target.id,
        scraped_at=datetime(2026, 2, 24, 19, 4, 1),
        title="Far infrared heating pad",
        brand="Example",
        rating_value=4.5,
        rating_count=123,
        current_price=39.99,
        currency="USD",
        bsr_rank=10,
        bsr_category="Heating Pads",
        bullet_points=["Comfortable heat"],
        product_info={"Material": "Graphene"},
        attributes={},
        images={},
        videos={},
        customers_say={"topics": [{"name": "Comfort", "mention_count": 10}]},
        qa_content=[],
        aplus_content={},
        source_url="https://www.amazon.com/dp/B012345678",
        content_hash="a" * 64,
        raw_payload={},
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def test_human_edit_cannot_be_silently_overwritten(db):
    target = category(db)
    listing = add_listing(db, target)
    suggestion = generate_draft(db, target)["suggestions"][0]
    save_section(
        db,
        category=target,
        section_key=suggestion["section_key"],
        content=suggestion["content"],
        evidence_listing_ids=[listing.id],
        generation_mode="generated",
        actor="system",
    )
    save_section(
        db,
        category=target,
        section_key="definition",
        content="Business-approved definition",
        evidence_listing_ids=[listing.id],
        generation_mode="human",
        actor="researcher",
    )

    with pytest.raises(WorkflowError, match="locked"):
        save_section(
            db,
            category=target,
            section_key="definition",
            content="Generated replacement",
            evidence_listing_ids=[listing.id],
            generation_mode="generated",
            actor="system",
        )

    stored = db.scalar(
        select(EncyclopediaSection).where(
            EncyclopediaSection.category_id == target.id,
            EncyclopediaSection.section_key == "definition",
        )
    )
    assert stored.content == "Business-approved definition"


def test_review_and_local_publication_are_auditable(db):
    target = category(db)
    listing = add_listing(db, target)
    save_section(
        db,
        category=target,
        section_key="definition",
        content="Reviewed content",
        evidence_listing_ids=[listing.id],
        generation_mode="human",
        actor="researcher",
    )
    version = submit_for_review(db, category=target, actor="researcher", note="MVP")
    assert version.status == "pending_review"

    version = review_version(
        db, version=version, decision="approve", comment="Approved", actor="reviewer"
    )
    assert version.status == "approved"
    reviewed_section = db.scalar(
        select(EncyclopediaSection).where(
            EncyclopediaSection.category_id == target.id,
            EncyclopediaSection.section_key == "definition",
        )
    )
    assert reviewed_section.review_status == "approved"

    publication = publish_version(
        db, version=version, provider_name="local", actor="reviewer"
    )
    assert publication.status == "published"
    assert publication.external_doc_id == f"local-preview-{version.id}"
    assert "Reviewed content" in publication.preview_content

    same_publication = publish_version(
        db, version=version, provider_name="local", actor="reviewer"
    )
    assert same_publication.id == publication.id


def test_evidence_must_belong_to_the_selected_category(db):
    target = category(db)
    other = category(db, "SHOULDER_NECK_HEAT_THERAPY")
    listing = add_listing(db, other)

    with pytest.raises(WorkflowError, match="belong"):
        save_section(
            db,
            category=target,
            section_key="definition",
            content="Invalid evidence",
            evidence_listing_ids=[listing.id],
            generation_mode="human",
            actor="researcher",
        )


def test_category_cannot_have_multiple_pending_versions(db):
    target = category(db)
    listing = add_listing(db, target)
    save_section(
        db,
        category=target,
        section_key="definition",
        content="Pending content",
        evidence_listing_ids=[listing.id],
        generation_mode="human",
        actor="researcher",
    )
    submit_for_review(db, category=target, actor="researcher", note=None)

    with pytest.raises(WorkflowError, match="already"):
        submit_for_review(db, category=target, actor="researcher", note=None)


def test_submitted_category_cannot_be_edited_in_place(db):
    target = category(db)
    listing = add_listing(db, target)
    save_section(
        db,
        category=target,
        section_key="definition",
        content="Locked definition",
        evidence_listing_ids=[listing.id],
        generation_mode="human",
        actor="researcher",
    )
    submit_for_review(db, category=target, actor="researcher", note=None)

    with pytest.raises(WorkflowError, match="锁定"):
        save_section(
            db,
            category=target,
            section_key="definition",
            content="Edited after submit",
            evidence_listing_ids=[listing.id],
            generation_mode="human",
            actor="researcher",
        )
