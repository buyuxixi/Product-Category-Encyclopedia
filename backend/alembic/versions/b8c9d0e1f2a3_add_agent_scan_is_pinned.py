"""add is_pinned to agent_scans

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agent_scans",
        sa.Column(
            "is_pinned",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
            comment="是否顶置到历史列表顶部",
        ),
    )
    op.create_index(op.f("ix_agent_scans_is_pinned"), "agent_scans", ["is_pinned"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_scans_is_pinned"), table_name="agent_scans")
    op.drop_column("agent_scans", "is_pinned")
