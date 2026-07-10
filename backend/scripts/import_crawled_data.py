"""Bulk import: write crawled category data into the database.

This script:
1. Parses the 5 category encyclopedia .md files into section content
2. Writes section content into encyclopedia_sections
3. Inserts raw data files as source_materials
4. Creates evidence_links connecting sources to sections

Run: cd backend && PYTHONPATH="" .venv/bin/python scripts/import_crawled_data.py
"""

import os
import re
from datetime import UTC, datetime

from app.database import SessionLocal, engine
from app.models import (
    AuditEvent,
    Category,
    EncyclopediaSection,
    EvidenceLink,
    SourceMaterial,
)
from sqlalchemy import select, text

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")

CATEGORY_FILE_MAP = {
    "TENS_THERAPY": "tens_therapy.md",
    "HEAT_THERAPY": "heat_therapy.md",
    "NIGHT_LIGHT": "night_light.md",
    "MEDICATION_MANAGEMENT": "medication_management.md",
    "SEAT_CUSHION": "seat_cushion.md",
}

WIKI_URLS = {
    "tens_wiki": "https://en.wikipedia.org/wiki/Transcutaneous_electrical_nerve_stimulation",
    "TENS_device_wiki": "https://en.wikipedia.org/wiki/TENS_unit",
    "Neurostimulation_wiki": "https://en.wikipedia.org/wiki/Neurostimulation",
    "Electrical_stimulation_wiki": "https://en.wikipedia.org/wiki/Electrical_muscle_stimulation",
    "electrotherapy_wiki": "https://en.wikipedia.org/wiki/Electrotherapy",
    "Pain_management_wiki": "https://en.wikipedia.org/wiki/Pain_management",
    "Chronic_pain_wiki": "https://en.wikipedia.org/wiki/Chronic_pain",
    "heat_therapy_wiki": "https://en.wikipedia.org/wiki/Heat_therapy",
    "Thermotherapy_wiki": "https://en.wikipedia.org/wiki/Thermotherapy",
    "Heating_pad_wiki": "https://en.wikipedia.org/wiki/Heating_pad",
    "far_infrared_wiki": "https://en.wikipedia.org/wiki/Infrared_heater",
    "infrared_therapy_wiki": "https://en.wikipedia.org/wiki/Infrared_lamp",
    "Infrared_lamp_wiki": "https://en.wikipedia.org/wiki/Infrared_lamp",
    "Hot_water_bottle_wiki": "https://en.wikipedia.org/wiki/Hot_water_bottle",
    "Electric_heating_pad_wiki": "https://en.wikipedia.org/wiki/Infrared_heater",
    "Warm_compress_wiki": "https://en.wikipedia.org/wiki/Warm_compress",
    "Arthritis_wiki": "https://en.wikipedia.org/wiki/Arthritis",
    "Menstrual_pain_wiki": "https://en.wikipedia.org/wiki/Dysmenorrhea",
    "Diabetic_neuropathy_wiki": "https://en.wikipedia.org/wiki/Diabetic_neuropathy",
    "Nightlight_wiki": "https://en.wikipedia.org/wiki/Nightlight",
    "night_light_wiki": "https://en.wikipedia.org/wiki/Nightlight",
    "Smart_lighting_wiki": "https://en.wikipedia.org/wiki/Smart_lighting",
    "motion_sensor_wiki": "https://en.wikipedia.org/wiki/Passive_infrared_sensor",
    "Circadian_rhythm_wiki": "https://en.wikipedia.org/wiki/Circadian_rhythm",
    "Melatonin_wiki": "https://en.wikipedia.org/wiki/Melatonin",
    "Sleep_hygiene_wiki": "https://en.wikipedia.org/wiki/Sleep_hygiene",
    "Illuminance_wiki": "https://en.wikipedia.org/wiki/Illuminance",
    "Lumen_wiki": "https://en.wikipedia.org/wiki/Lumen_(unit)",
    "smart_home_wiki": "https://en.wikipedia.org/wiki/Home_automation",
    "Medication_organizer_wiki": "https://en.wikipedia.org/wiki/Pill_organizer",
    "pill_organizer_wiki": "https://en.wikipedia.org/wiki/Pill_organizer",
    "Medication_splitter_wiki": "https://en.wikipedia.org/wiki/Pill_splitter",
    "pill_splitter_wiki": "https://en.wikipedia.org/wiki/Pill_splitter",
    "Medication_adherence_wiki": "https://en.wikipedia.org/wiki/Medication_adherence",
    "Medication_management_wiki": "https://en.wikipedia.org/wiki/Medication_management",
    "Medication_error_wiki": "https://en.wikipedia.org/wiki/Medication_error",
    "Polypharmacy_wiki": "https://en.wikipedia.org/wiki/Polypharmacy",
    "memory_foam_wiki": "https://en.wikipedia.org/wiki/Memory_foam",
    "ergonomics_wiki": "https://en.wikipedia.org/wiki/Ergonomics",
    "seat_cushion_wiki": "https://en.wikipedia.org/wiki/Cushion",
    "orthopedic_cushion_wiki": "https://en.wikipedia.org/wiki/Orthopedics",
    "Orthopedic_pillow_wiki": "https://en.wikipedia.org/wiki/Orthopedic_pillow",
}

OTHER_URLS = {
    "tens_harvard": "https://www.health.harvard.edu/pain/transcutaneous-electrical-nerve-stimulation-tens-for-pain-management",
    "tens_hopkins": "https://www.hopkinsmedicine.org/health/treatment-tests-and-therapies/transcutaneous-electrical-nerve-stimulation",
    "tens_mayoclinic": "https://www.mayoclinic.org/tests-procedures/tens/home/ovc-20336467",
    "heat_harvard": "https://www.health.harvard.edu/pain/heat-and-cold-for-pain-relief",
    "heat_arthritis": "https://www.arthritis.org/health-wellness/healthy-living/managing-arthritis/daily-living/easy-stuff/best-heat-cold-pain-relief",
    "heat_therapy_arthritis": "https://www.arthritis.org/health-wellness/healthy-living/managing-arthritis/daily-living/easy-stuff/best-heat-cold-pain-relief",
    "lighting_harvard": "https://www.health.harvard.edu/staying-healthy/blue-light-has-a-dark-side",
    "nightlight_sleepfoundation": "https://www.sleepfoundation.org/bedroom-environment/night-lights",
    "pill_nia": "https://www.nia.nih.gov/health/medicines-and-medication-management",
    "seatcushion_spinehealth": "https://www.spine-health.com/wellness/ergonomics/ergonomic-seat-cushions",
    "ergonomics_niosh": "https://www.cdc.gov/niosh/topics/ergonomics/",
}


def get_url(filename: str) -> str | None:
    base = filename.replace(".txt", "")
    if base in WIKI_URLS:
        return WIKI_URLS[base]
    if base in OTHER_URLS:
        return OTHER_URLS[base]
    return None


def classify_raw_file(filename: str) -> str | None:
    f = filename.lower()
    if any(x in f for x in ["tens", "electrotherapy", "electrical_stimulation", "neurostimulation", "pain_management", "chronic_pain", "diabetic_neuropathy"]):
        return "TENS_THERAPY"
    if any(x in f for x in ["heat", "thermotherapy", "infrared", "heating", "hot_water", "warm_compress", "far_infrared", "arthritis", "menstrual"]):
        return "HEAT_THERAPY"
    if any(x in f for x in ["night", "nightlight", "circadian", "melatonin", "sleep", "illuminance", "lumen", "motion_sensor", "smart_lighting", "smart_home", "lighting"]):
        return "NIGHT_LIGHT"
    if any(x in f for x in ["pill", "medication", "polypharmacy"]):
        return "MEDICATION_MANAGEMENT"
    if any(x in f for x in ["seat", "cushion", "memory_foam", "orthopedic", "ergonomic", "niosh"]):
        return "SEAT_CUSHION"
    return None


def get_section_keys_for_file(filename: str) -> set[str]:
    f = filename.lower()
    sections: set[str] = set()

    if any(x in f for x in ["pill_organizer", "pill_splitter", "cushion", "tens_wiki", "heat_therapy_wiki", "nightlight", "night_light_wiki", "tens_device"]):
        sections.add("definition")
    if any(x in f for x in ["arthritis", "menstrual", "diabetic", "chronic_pain", "sleep_hygiene", "polypharmacy", "ergonomic"]):
        sections.add("users")
    if any(x in f for x in ["pain_management", "medication_adherence", "medication_error", "chronic_pain", "arthritis", "menstrual", "diabetic"]):
        sections.add("needs")
    if any(x in f for x in ["electrotherapy", "infrared", "heating", "memory_foam", "motion_sensor", "melatonin", "circadian", "electrical_stimulation", "neurostimulation"]):
        sections.add("technology")
    if any(x in f for x in ["smart_lighting", "smart_home", "neurostimulation"]):
        sections.add("trends")
    if any(x in f for x in ["circadian", "melatonin", "sleep", "lighting", "illuminance", "lumen"]):
        sections.add("market")

    if not sections:
        sections.add("sources")
    return sections


def map_section_key(section_name: str) -> str | None:
    for cn_num, key in [
        ("\u4e00", "definition"),
        ("\u4e8c", "users"),
        ("\u4e09", "needs"),
        ("\u56db", "technology"),
        ("\u4e94", "trends"),
        ("\u516d", "market"),
        ("\u4e03", "sources"),
    ]:
        if section_name.startswith(cn_num):
            return key
    return None


def parse_md_sections(filepath: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_name: str | None = None
    current_lines: list[str] = []

    with open(filepath, encoding="utf-8") as f:
        for line in f:
            if re.match(r"^## [^#]", line):
                if current_name is not None:
                    sections[map_section_key(current_name)] = "\n".join(current_lines).strip()
                current_name = line[3:].strip()
                current_lines = []
            elif current_name is not None:
                current_lines.append(line)
        if current_name is not None:
            sections[map_section_key(current_name)] = "\n".join(current_lines).strip()
    return sections


def main() -> None:
    db = SessionLocal()

    # --- Step 1: Write section content ---
    total_sections = 0
    for cat_code, filename in CATEGORY_FILE_MAP.items():
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            print(f"  SKIP {cat_code} — file not found: {filepath}")
            continue

        category = db.scalar(select(Category).where(Category.code == cat_code))
        if not category:
            print(f"  SKIP {cat_code} — category not in DB")
            continue

        sections = parse_md_sections(filepath)
        for section_key, content in sections.items():
            if not section_key or not content:
                continue
            section = db.scalar(
                select(EncyclopediaSection).where(
                    EncyclopediaSection.category_id == category.id,
                    EncyclopediaSection.section_key == section_key,
                )
            )
            if section:
                section.content = content
                section.generation_mode = "generated"
                section.review_status = "draft"
                section.updated_by = "system_seed"
                total_sections += 1
        db.flush()

    db.commit()
    print(f"Step 1 — Section content written: {total_sections} sections across {len(CATEGORY_FILE_MAP)} categories")

    # --- Step 2: Insert source_materials ---
    cat_map = {cat.code: cat for cat in db.scalars(select(Category))}
    inserted_sources = 0
    source_map: dict[str, list[tuple[int, str, set[str]]]] = {}

    for filename in sorted(os.listdir(RAW_DIR)):
        if not filename.endswith(".txt"):
            continue

        cat_code = classify_raw_file(filename)
        if not cat_code or cat_code not in cat_map:
            continue

        category = cat_map[cat_code]
        filepath = os.path.join(RAW_DIR, filename)

        with open(filepath, errors="ignore") as f:
            content = f.read()

        if len(content) > 50000:
            content = content[:50000] + "...[truncated]"

        url = get_url(filename)
        title = filename.replace("_wiki.txt", " (Wikipedia)").replace(".txt", "").replace("_", " ").title()
        if "wiki" in filename and "Wikipedia" not in title:
            title = filename.replace(".txt", "").replace("_", " ").title() + " (Wikipedia)"

        source = SourceMaterial(
            category_id=category.id,
            source_type="research",
            title=title,
            url=url,
            content=content,
            collected_at=datetime.now(UTC),
            created_by="system_seed",
        )
        db.add(source)
        db.flush()

        section_keys = get_section_keys_for_file(filename)
        source_map.setdefault(cat_code, []).append((source.id, filename, section_keys))
        inserted_sources += 1

    db.commit()
    print(f"Step 2 — Source materials inserted: {inserted_sources}")

    # --- Step 3: Create evidence_links ---
    inserted_evidence = 0
    for cat_code, sources in source_map.items():
        category = cat_map[cat_code]
        for source_id, _filename, section_keys in sources:
            for section_key in section_keys:
                section = db.scalar(
                    select(EncyclopediaSection).where(
                        EncyclopediaSection.category_id == category.id,
                        EncyclopediaSection.section_key == section_key,
                    )
                )
                if section and section.content.strip():
                    db.add(EvidenceLink(
                        section_id=section.id,
                        source_type="source_material",
                        source_id=source_id,
                        locator="Registered source material",
                    ))
                    inserted_evidence += 1

    db.commit()
    print(f"Step 3 — Evidence links created: {inserted_evidence}")

    # --- Audit event ---
    db.add(AuditEvent(
        actor="system_seed",
        action="bulk_data_import",
        entity_type="source_material",
        entity_id="bulk",
        metadata_json={
            "sources_inserted": inserted_sources,
            "evidence_links": inserted_evidence,
            "sections_written": total_sections,
        },
    ))
    db.commit()

    # --- Verify ---
    with engine.connect() as conn:
        for table in ["source_materials", "evidence_links", "encyclopedia_sections"]:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"  {table}: {count}")

        print("\nPer-category breakdown:")
        for row in conn.execute(text("""
            SELECT c.code, c.name,
                   COUNT(DISTINCT sm.id) as sources,
                   COUNT(DISTINCT s.id) as sections_with_content
            FROM categories c
            LEFT JOIN source_materials sm ON sm.category_id = c.id
            LEFT JOIN encyclopedia_sections s ON s.category_id = c.id AND LENGTH(s.content) > 0
            WHERE c.parent_id IS NULL
            GROUP BY c.id ORDER BY c.id
        """)):
            print(f"  {row[0]:25s} {row[1]:20s}  sources={row[2]:>3}  sections={row[3]}")

    db.close()
    print("\n✅ Import complete!")


if __name__ == "__main__":
    main()
