"""sync audit event indexes with the ORM model

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-13
"""

from typing import Sequence, Union

from alembic import op


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_audit_events_entity_id", table_name="audit_events")


def downgrade() -> None:
    op.create_index(
        "ix_audit_events_entity_id",
        "audit_events",
        ["entity_id"],
        unique=False,
    )
