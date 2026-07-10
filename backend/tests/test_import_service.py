from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import func, select

from app.config import get_settings
from app.models import ListingSnapshot
from app.services.import_service import import_amazon_directories


def payload(asin: str = "B012345678") -> dict:
    return {
        "url": f"https://www.amazon.com/dp/{asin}",
        "asin": asin,
        "scraped_at": "2026-02-24 19:04:01",
        "success": True,
        "error": None,
        "title": "Far infrared heating pad",
        "brand": "Example",
        "rating": {"star_rating": 4.5, "rating_count": 123},
        "prices": {"current_price": 39.99, "currency": "USD"},
        "product_info": {"Material": "Graphene"},
        "attributes": {},
        "images": {},
        "videos": {},
        "bullet_points": ["Heat therapy"],
        "customers_say": {"topics": [{"name": "Comfort", "mention_count": 10}]},
        "qa_content": [],
        "aplus_content": {},
        "cookies": {"session": "must-not-be-stored"},
        "bsr_category": "Heating Pads",
        "bsr_rank": 10,
    }


def write_listing(directory: Path, data: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{data['asin']}.json").write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8"
    )


def test_import_deduplicates_alias_directories(db, tmp_path, monkeypatch):
    write_listing(tmp_path / "FAR_INFRARED", payload())
    write_listing(tmp_path / "Far-infrared", payload())
    monkeypatch.setenv("IMPORT_ROOTS", str(tmp_path))
    get_settings.cache_clear()

    job = import_amazon_directories(
        db,
        root_path=str(tmp_path),
        requested_directories=["FAR_INFRARED", "Far-infrared"],
        actor="tester",
    )

    assert job.status == "completed"
    assert job.total_count == 2
    assert job.inserted_count == 1
    assert job.duplicate_count == 1
    assert db.scalar(select(func.count()).select_from(ListingSnapshot)) == 1


def test_import_records_bad_json_without_aborting_batch(db, tmp_path, monkeypatch):
    directory = tmp_path / "FAR_INFRARED"
    write_listing(directory, payload())
    (directory / "B087654321.json").write_text("{broken", encoding="utf-8")
    monkeypatch.setenv("IMPORT_ROOTS", str(tmp_path))
    get_settings.cache_clear()

    job = import_amazon_directories(
        db,
        root_path=str(tmp_path),
        requested_directories=["FAR_INFRARED"],
        actor="tester",
    )

    assert job.status == "completed_with_errors"
    assert job.inserted_count == 1
    assert job.failed_count == 1
    assert job.errors[0]["file"] == "B087654321.json"


def test_import_rejects_payload_when_asin_does_not_match_filename(db, tmp_path, monkeypatch):
    directory = tmp_path / "FAR_INFRARED"
    directory.mkdir(parents=True)
    (directory / "B087654321.json").write_text(
        json.dumps(payload("B012345678")), encoding="utf-8"
    )
    monkeypatch.setenv("IMPORT_ROOTS", str(tmp_path))
    get_settings.cache_clear()

    job = import_amazon_directories(
        db,
        root_path=str(tmp_path),
        requested_directories=["FAR_INFRARED"],
        actor="tester",
    )

    assert job.inserted_count == 0
    assert job.failed_count == 1
    assert "does not match" in job.errors[0]["reason"]


def test_import_supports_csv_and_removes_sensitive_payload_keys(db, tmp_path, monkeypatch):
    directory = tmp_path / "FAR_INFRARED"
    write_listing(directory, payload())
    (directory / "listings.csv").write_text(
        "asin,scraped_at,title,brand,price,rating\n"
        "B098765432,2026-02-24 19:04:01,CSV heating pad,CSV Brand,29.99,4.2\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("IMPORT_ROOTS", str(tmp_path))
    get_settings.cache_clear()

    job = import_amazon_directories(
        db,
        root_path=str(tmp_path),
        requested_directories=["FAR_INFRARED"],
        actor="tester",
    )

    assert job.status == "completed"
    assert job.total_count == 2
    assert job.inserted_count == 2
    stored = db.scalar(select(ListingSnapshot).where(ListingSnapshot.asin == "B012345678"))
    assert stored is not None
    assert "cookies" not in stored.raw_payload
