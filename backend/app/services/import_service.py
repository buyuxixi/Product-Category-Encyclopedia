from __future__ import annotations

import hashlib
import json
import re
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AuditEvent, Category, EncyclopediaSection, ImportJob, ListingSnapshot


DIRECTORY_CATEGORY_MAP = {
    "FAR_INFRARED": "FAR_INFRARED",
    "Far-infrared": "FAR_INFRARED",
    "SUB_SHOULDER_NECK_HEAT_THERAPY": "SHOULDER_NECK_HEAT_THERAPY",
    "Neck Heat Therapy-Back Heat Therapy": "SHOULDER_NECK_HEAT_THERAPY",
}
CURATED_CATEGORY_NAMES = {
    "HEAT_THERAPY": "热疗",
    "FAR_INFRARED": "远红外热疗",
    "SHOULDER_NECK_HEAT_THERAPY": "肩颈热敷",
}
SENSITIVE_PAYLOAD_KEYS = {
    "authorization",
    "cookie",
    "cookies",
    "password",
    "refresh_token",
    "secret",
    "session",
    "session_id",
    "token",
    "access_token",
}
ASIN_PATTERN = re.compile(r"^B[A-Z0-9]{9}$")
MAX_LISTING_FILE_BYTES = 20 * 1024 * 1024


class ImportValidationError(ValueError):
    pass


def _directory_code(directory_name: str) -> str:
    if directory_name in DIRECTORY_CATEGORY_MAP:
        return DIRECTORY_CATEGORY_MAP[directory_name]
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", directory_name).strip("_").upper()
    normalized = re.sub(r"_(?:\d+)$", "", normalized)
    normalized = re.sub(r"^SUB_", "", normalized)
    return normalized[:80] or "UNNAMED_CATEGORY"


def _display_name(directory_names: list[str], code: str) -> str:
    if code in CURATED_CATEGORY_NAMES:
        return CURATED_CATEGORY_NAMES[code]
    preferred = sorted(
        directory_names,
        key=lambda item: (item.isupper(), item.startswith("SUB_"), len(item)),
    )[0]
    return re.sub(r"\s+", " ", re.sub(r"[_-]+", " ", preferred.replace("SUB_", ""))).strip().title()


def _directory_groups(root: Path) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = defaultdict(list)
    for path in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if path.name.startswith(".") or not path.is_dir() or path.is_symlink():
            continue
        groups[_directory_code(path.name)].append(path)
    return dict(groups)


def list_import_catalog(root_path: str) -> list[dict[str, Any]]:
    root = _safe_import_path(root_path)
    if not root.is_dir():
        raise ImportValidationError("Import root does not exist or is not a directory")
    result: list[dict[str, Any]] = []
    for code, directories in _directory_groups(root).items():
        json_count = sum(
            1 for directory in directories if any(directory.glob("*.json"))
        )
        file_count = sum(1 for directory in directories for item in directory.iterdir() if item.is_file())
        result.append(
            {
                "code": code,
                "name": _display_name([item.name for item in directories], code),
                "directories": [item.name for item in directories],
                "file_count": file_count,
                "json_directory_count": json_count,
            }
        )
    return sorted(result, key=lambda item: item["name"])


def _sanitize_payload(value: Any, key: str | None = None, depth: int = 0) -> Any:
    if key and key.lower() in SENSITIVE_PAYLOAD_KEYS:
        return None
    if depth > 12:
        return "[truncated]"
    if isinstance(value, dict):
        return {
            str(child_key): _sanitize_payload(child_value, str(child_key), depth + 1)
            for child_key, child_value in value.items()
            if str(child_key).lower() not in SENSITIVE_PAYLOAD_KEYS
        }
    if isinstance(value, list):
        return [_sanitize_payload(item, depth=depth + 1) for item in value]
    return value


def _ensure_category(db: Session, directory_names: list[str], code: str) -> Category:
    category = db.scalar(select(Category).where(Category.code == code))
    if category is None:
        category = Category(
            code=code,
            name=_display_name(directory_names, code),
            aliases=directory_names,
            included_items=[],
            excluded_items=[],
            description=f"来自 Amazon 数据目录 {directory_names[0]}，待业务人员补充品类定义。",
        )
        db.add(category)
        db.flush()
    else:
        category.aliases = sorted(set((category.aliases or []) + directory_names))

    existing_keys = set(
        db.scalars(
            select(EncyclopediaSection.section_key).where(
                EncyclopediaSection.category_id == category.id
            )
        ).all()
    )
    section_definitions = [
        ("definition", "品类定义与边界"),
        ("users", "用户画像与使用场景"),
        ("needs", "用户需求与品类痛点"),
        ("technology", "技术、材料与设计原则"),
        ("trends", "新兴趋势"),
        ("market", "舆情与市场趋势"),
    ]
    for section_key, title in section_definitions:
        if section_key not in existing_keys:
            db.add(
                EncyclopediaSection(
                    category_id=category.id,
                    section_key=section_key,
                    title=title,
                )
            )
    db.flush()
    return category


def _safe_import_path(raw_path: str) -> Path:
    configured_roots = get_settings().import_roots
    if raw_path == "/imports" and len(configured_roots) == 1:
        candidate = configured_roots[0]
    else:
        candidate = Path(raw_path).expanduser().resolve()
    for root in configured_roots:
        try:
            candidate.relative_to(root)
            return candidate
        except ValueError:
            continue
    raise ImportValidationError("Import path is outside configured import roots")


def _parse_datetime(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ImportValidationError("scraped_at is required")
    normalized = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ImportValidationError("scraped_at is invalid") from exc


def _number(value: Any, cast):
    if value in (None, ""):
        return None
    try:
        return cast(value)
    except (TypeError, ValueError):
        return None


def _listing_from_payload(
    payload: dict[str, Any], category_id: int, expected_asin: str | None = None
) -> ListingSnapshot:
    asin = payload.get("asin")
    if not isinstance(asin, str) or not ASIN_PATTERN.fullmatch(asin):
        raise ImportValidationError("ASIN is missing or invalid")
    if expected_asin is not None and asin != expected_asin:
        raise ImportValidationError("Payload ASIN does not match the file name")
    if payload.get("success") is not True:
        raise ImportValidationError("Listing scrape was not successful")

    rating = payload.get("rating") if isinstance(payload.get("rating"), dict) else {}
    prices = payload.get("prices") if isinstance(payload.get("prices"), dict) else {}
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    sanitized_payload = _sanitize_payload(payload)
    return ListingSnapshot(
        marketplace="US",
        asin=asin,
        category_id=category_id,
        scraped_at=_parse_datetime(payload.get("scraped_at")),
        title=str(payload.get("title") or ""),
        brand=str(payload.get("brand") or ""),
        rating_value=_number(rating.get("star_rating"), float),
        rating_count=_number(rating.get("rating_count"), int),
        current_price=_number(prices.get("current_price"), float),
        currency=prices.get("currency") or None,
        bsr_rank=_number(payload.get("bsr_rank"), int),
        bsr_category=payload.get("bsr_category") or None,
        bullet_points=sanitized_payload.get("bullet_points") or [],
        product_info=sanitized_payload.get("product_info") or {},
        attributes=sanitized_payload.get("attributes") or {},
        images=sanitized_payload.get("images") or {},
        videos=sanitized_payload.get("videos") or {},
        customers_say=sanitized_payload.get("customers_say") or {},
        qa_content=sanitized_payload.get("qa_content") or [],
        aplus_content=sanitized_payload.get("aplus_content") or {},
        source_url=payload.get("url") or None,
        content_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        raw_payload=sanitized_payload,
    )


def _csv_value(row: dict[str, Any], *keys: str) -> Any:
    normalized = {str(key).strip().lower(): value for key, value in row.items()}
    for key in keys:
        value = normalized.get(key.lower())
        if value not in (None, ""):
            return value
    return None


def _parse_csv_json(value: Any, fallback: Any) -> Any:
    if not isinstance(value, str) or not value.strip():
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _read_listing_payloads(file_path: Path) -> list[tuple[dict[str, Any], str | None, str]]:
    if file_path.suffix.lower() == ".json":
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ImportValidationError("JSON root must be an object")
        return [(payload, file_path.stem, file_path.name)]

    with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ImportValidationError("CSV header is missing")
        payloads: list[tuple[dict[str, Any], str | None, str]] = []
        for row_number, row in enumerate(reader, start=2):
            asin = _csv_value(row, "asin", "ASIN")
            payloads.append(
                (
                    {
                        "asin": asin,
                        "scraped_at": _csv_value(row, "scraped_at", "collected_at", "date"),
                        "success": str(_csv_value(row, "success") or "true").lower()
                        in {"1", "true", "yes", "y"},
                        "url": _csv_value(row, "url", "source_url"),
                        "title": _csv_value(row, "title", "name") or "",
                        "brand": _csv_value(row, "brand") or "",
                        "rating": {
                            "star_rating": _csv_value(row, "star_rating", "rating_value", "rating"),
                            "rating_count": _csv_value(row, "rating_count", "reviews"),
                        },
                        "prices": {
                            "current_price": _csv_value(row, "current_price", "price"),
                            "currency": _csv_value(row, "currency") or "USD",
                        },
                        "bsr_rank": _csv_value(row, "bsr_rank", "bsr"),
                        "bsr_category": _csv_value(row, "bsr_category"),
                        "bullet_points": [
                            item.strip()
                            for item in str(_csv_value(row, "bullet_points") or "").split("|")
                            if item.strip()
                        ],
                        "product_info": _parse_csv_json(
                            _csv_value(row, "product_info", "attributes"), {}
                        ),
                        "attributes": {},
                        "images": {},
                        "videos": {},
                        "customers_say": _parse_csv_json(
                            _csv_value(row, "customers_say", "review_topics"), {}
                        ),
                        "qa_content": [],
                        "aplus_content": {},
                    },
                    None,
                    f"{file_path.name}:row {row_number}",
                )
            )
        return payloads


def import_amazon_directories(
    db: Session,
    *,
    root_path: str,
    requested_directories: list[str] | None,
    actor: str,
) -> ImportJob:
    root = _safe_import_path(root_path)
    if not root.is_dir():
        raise ImportValidationError("Import root does not exist or is not a directory")

    available_directories = {
        directory.name
        for directory in root.iterdir()
        if directory.is_dir() and not directory.name.startswith(".") and not directory.is_symlink()
    }
    directories = list(requested_directories) if requested_directories is not None else sorted(available_directories)
    unknown = sorted(set(directories) - available_directories)
    if unknown:
        raise ImportValidationError(f"Directories are missing: {', '.join(unknown)}")
    if not directories:
        raise ImportValidationError("At least one import directory must be selected")

    job = ImportJob(
        status="running",
        source_path=str(root),
        requested_directories=directories,
        created_by=actor,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    errors: list[dict[str, str]] = []
    for directory_name in directories:
        directory = _safe_import_path(str(root / directory_name))
        if directory.parent != root or not directory.is_dir():
            errors.append({"file": directory_name, "reason": "Directory is missing"})
            job.failed_count += 1
            continue

        code = _directory_code(directory_name)
        same_code_names = [
            name for name in directories if _directory_code(name) == code
        ]
        category = _ensure_category(db, same_code_names, code)
        file_paths = sorted([*directory.glob("*.json"), *directory.glob("*.csv")])
        for file_path in file_paths:
            if file_path.name.startswith(".") or (
                file_path.suffix.lower() == ".json" and not ASIN_PATTERN.fullmatch(file_path.stem)
            ):
                job.skipped_count += 1
                continue
            try:
                if file_path.is_symlink():
                    raise ImportValidationError("Symbolic links are not allowed")
                if file_path.stat().st_size > MAX_LISTING_FILE_BYTES:
                    raise ImportValidationError("Listing file exceeds the 20 MB limit")
                payloads = _read_listing_payloads(file_path)
            except (OSError, json.JSONDecodeError, csv.Error, ImportValidationError) as exc:
                job.total_count += 1
                job.failed_count += 1
                if len(errors) < 100:
                    errors.append({"file": file_path.name, "reason": str(exc)[:240]})
                continue

            for payload, expected_asin, label in payloads:
                job.total_count += 1
                try:
                    listing = _listing_from_payload(
                        payload, category.id, expected_asin=expected_asin
                    )
                    exists = db.scalar(
                        select(ListingSnapshot.id).where(
                            ListingSnapshot.marketplace == listing.marketplace,
                            ListingSnapshot.asin == listing.asin,
                            ListingSnapshot.scraped_at == listing.scraped_at,
                        )
                    )
                    if exists:
                        job.duplicate_count += 1
                        continue
                    with db.begin_nested():
                        db.add(listing)
                        db.flush()
                    job.inserted_count += 1
                except (OSError, json.JSONDecodeError, csv.Error, ImportValidationError, SQLAlchemyError) as exc:
                    job.failed_count += 1
                    if len(errors) < 100:
                        errors.append({"file": label, "reason": str(exc)[:240]})

    job.errors = errors
    job.status = "completed_with_errors" if job.failed_count else "completed"
    db.add(
        AuditEvent(
            actor=actor,
            action="amazon_import_completed",
            entity_type="import_job",
            entity_id=str(job.id),
            metadata_json={
                "inserted": job.inserted_count,
                "duplicates": job.duplicate_count,
                "failed": job.failed_count,
                "skipped": job.skipped_count,
            },
        )
    )
    db.commit()
    db.refresh(job)
    return job
