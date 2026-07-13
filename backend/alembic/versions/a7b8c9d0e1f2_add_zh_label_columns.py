"""add Chinese label columns

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "hot_links",
        sa.Column("title_zh", sa.String(length=200), nullable=True, comment="LLM生成的中文标题标签"),
    )
    op.add_column(
        "hot_links",
        sa.Column("description_zh", sa.Text(), nullable=True, comment="LLM生成的中文描述"),
    )
    op.add_column(
        "trend_signals",
        sa.Column("title_zh", sa.String(length=200), nullable=True, comment="LLM生成的中文标题标签"),
    )
    op.add_column(
        "trend_signals",
        sa.Column("summary_zh", sa.Text(), nullable=True, comment="LLM生成的中文摘要"),
    )


def downgrade() -> None:
    op.drop_column("trend_signals", "summary_zh")
    op.drop_column("trend_signals", "title_zh")
    op.drop_column("hot_links", "description_zh")
    op.drop_column("hot_links", "title_zh")
