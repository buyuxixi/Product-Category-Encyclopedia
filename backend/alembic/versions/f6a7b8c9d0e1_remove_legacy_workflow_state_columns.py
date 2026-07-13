"""remove legacy workflow state columns

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_categories_workflow_status", table_name="categories")
    op.drop_column("categories", "workflow_status")
    op.drop_column("encyclopedia_sections", "review_status")


def downgrade() -> None:
    op.add_column(
        "categories",
        sa.Column(
            "workflow_status",
            sa.String(length=32),
            nullable=False,
            server_default="data_preparation",
        ),
    )
    op.create_index(
        "ix_categories_workflow_status",
        "categories",
        ["workflow_status"],
        unique=False,
    )
    op.add_column(
        "encyclopedia_sections",
        sa.Column(
            "review_status",
            sa.String(length=32),
            nullable=False,
            server_default="draft",
        ),
    )
