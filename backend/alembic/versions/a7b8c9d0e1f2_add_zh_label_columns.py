"""add title_zh / description_zh / summary_zh columns to hot_links and trend_signals

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-07-13 18:00:00.000000

为 hot_links 和 trend_signals 表增加中文标签列：
  - hot_links:       title_zh (VARCHAR 200), description_zh (TEXT)
  - trend_signals:   title_zh (VARCHAR 200), summary_zh (TEXT)

所有新增列均 nullable，已有数据不受影响，前端将优先展示中文标签。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # hot_links
    op.add_column("hot_links", sa.Column("title_zh", sa.String(length=200), nullable=True))
    op.add_column("hot_links", sa.Column("description_zh", sa.Text(), nullable=True))

    # trend_signals
    op.add_column("trend_signals", sa.Column("title_zh", sa.String(length=200), nullable=True))
    op.add_column("trend_signals", sa.Column("summary_zh", sa.Text(), nullable=True))


def downgrade() -> None:
    # trend_signals
    op.drop_column("trend_signals", "summary_zh")
    op.drop_column("trend_signals", "title_zh")

    # hot_links
    op.drop_column("hot_links", "description_zh")
    op.drop_column("hot_links", "title_zh")
