"""remove legacy import review publication tables

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LEGACY_TABLES = (
    "publication_records",
    "encyclopedia_versions",
    "import_jobs",
    "listing_snapshots",
)


def upgrade() -> None:
    bind = op.get_bind()
    non_empty = {
        table: int(bind.execute(sa.text(f"SELECT COUNT(*) FROM `{table}`")).scalar_one())
        for table in LEGACY_TABLES
    }
    non_empty = {table: count for table, count in non_empty.items() if count}
    if non_empty:
        raise RuntimeError(
            "Refusing to drop legacy workflow tables because they contain data: "
            + ", ".join(f"{table}={count}" for table, count in non_empty.items())
        )

    # Dropping the table also drops its indexes. On MySQL, the index backing the
    # version_id foreign key cannot be dropped independently before the table.
    op.drop_table("publication_records")

    op.drop_table("encyclopedia_versions")

    op.drop_table("import_jobs")

    op.drop_table("listing_snapshots")


def downgrade() -> None:
    op.create_table(
        "listing_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("marketplace", sa.String(length=16), nullable=False),
        sa.Column("asin", sa.String(length=20), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("scraped_at", sa.DateTime(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("brand", sa.String(length=255), nullable=False),
        sa.Column("rating_value", sa.Float(), nullable=True),
        sa.Column("rating_count", sa.Integer(), nullable=True),
        sa.Column("current_price", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=True),
        sa.Column("bsr_rank", sa.Integer(), nullable=True),
        sa.Column("bsr_category", sa.String(length=255), nullable=True),
        sa.Column("bullet_points", sa.JSON(), nullable=False),
        sa.Column("product_info", sa.JSON(), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("images", sa.JSON(), nullable=False),
        sa.Column("videos", sa.JSON(), nullable=False),
        sa.Column("customers_say", sa.JSON(), nullable=False),
        sa.Column("qa_content", sa.JSON(), nullable=False),
        sa.Column("aplus_content", sa.JSON(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("marketplace", "asin", "scraped_at", name="uq_listing_snapshot"),
    )
    op.create_index("ix_listing_category_brand", "listing_snapshots", ["category_id", "brand"], unique=False)
    op.create_index("ix_listing_snapshots_asin", "listing_snapshots", ["asin"], unique=False)
    op.create_index("ix_listing_snapshots_brand", "listing_snapshots", ["brand"], unique=False)
    op.create_index("ix_listing_snapshots_category_id", "listing_snapshots", ["category_id"], unique=False)
    op.create_index("ix_listing_snapshots_content_hash", "listing_snapshots", ["content_hash"], unique=False)
    op.create_index("ix_listing_snapshots_marketplace", "listing_snapshots", ["marketplace"], unique=False)
    op.create_index("ix_listing_snapshots_scraped_at", "listing_snapshots", ["scraped_at"], unique=False)

    op.create_table(
        "import_jobs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("requested_directories", sa.JSON(), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("inserted_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_import_jobs_status", "import_jobs", ["status"], unique=False)

    op.create_table(
        "encyclopedia_versions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("content_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("reviewed_by", sa.String(length=120), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("category_id", "version_number", name="uq_category_version"),
    )
    op.create_index("ix_encyclopedia_versions_category_id", "encyclopedia_versions", ["category_id"], unique=False)
    op.create_index("ix_encyclopedia_versions_status", "encyclopedia_versions", ["status"], unique=False)

    op.create_table(
        "publication_records",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("version_id", sa.BigInteger(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("external_doc_id", sa.String(length=255), nullable=True),
        sa.Column("external_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("preview_content", sa.Text(), nullable=False),
        sa.Column("published_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["version_id"], ["encyclopedia_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "version_id", name="uq_provider_version"),
    )
    op.create_index("ix_publication_records_category_id", "publication_records", ["category_id"], unique=False)
    op.create_index("ix_publication_records_status", "publication_records", ["status"], unique=False)
    op.create_index("ix_publication_records_version_id", "publication_records", ["version_id"], unique=False)
