"""add trend_signals and hot_links tables

Revision ID: a1b2c3d4e5f6
Revises: f54e016350b3
Create Date: 2026-07-10 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '5b9e8d4a2c11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'trend_signals',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('section_key', sa.String(length=80), nullable=False),
        sa.Column('signal_type', sa.String(length=40), nullable=False),
        sa.Column('platform', sa.String(length=40), nullable=False),
        sa.Column('keyword', sa.String(length=500), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=True),
        sa.Column('metric_unit', sa.String(length=32), nullable=True),
        sa.Column('trend_direction', sa.String(length=16), nullable=True),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('collected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_trend_signals_category_id'), 'trend_signals', ['category_id'], unique=False)
    op.create_index(op.f('ix_trend_signals_section_key'), 'trend_signals', ['section_key'], unique=False)
    op.create_index(op.f('ix_trend_signals_signal_type'), 'trend_signals', ['signal_type'], unique=False)
    op.create_index(op.f('ix_trend_signals_platform'), 'trend_signals', ['platform'], unique=False)
    op.create_index(op.f('ix_trend_signals_collected_at'), 'trend_signals', ['collected_at'], unique=False)
    op.create_index('ix_trend_category_platform', 'trend_signals', ['category_id', 'platform'], unique=False)

    op.create_table(
        'hot_links',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('section_key', sa.String(length=80), nullable=False),
        sa.Column('link_type', sa.String(length=40), nullable=False),
        sa.Column('platform', sa.String(length=40), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('hotness_score', sa.Float(), nullable=True),
        sa.Column('is_hot', sa.Boolean(), nullable=False),
        sa.Column('collected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_hot_links_category_id'), 'hot_links', ['category_id'], unique=False)
    op.create_index(op.f('ix_hot_links_section_key'), 'hot_links', ['section_key'], unique=False)
    op.create_index(op.f('ix_hot_links_link_type'), 'hot_links', ['link_type'], unique=False)
    op.create_index(op.f('ix_hot_links_platform'), 'hot_links', ['platform'], unique=False)
    op.create_index(op.f('ix_hot_links_is_hot'), 'hot_links', ['is_hot'], unique=False)
    op.create_index(op.f('ix_hot_links_collected_at'), 'hot_links', ['collected_at'], unique=False)
    op.create_index('ix_hotlink_category_platform', 'hot_links', ['category_id', 'platform'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_hotlink_category_platform', table_name='hot_links')
    op.drop_index(op.f('ix_hot_links_collected_at'), table_name='hot_links')
    op.drop_index(op.f('ix_hot_links_is_hot'), table_name='hot_links')
    op.drop_index(op.f('ix_hot_links_platform'), table_name='hot_links')
    op.drop_index(op.f('ix_hot_links_link_type'), table_name='hot_links')
    op.drop_index(op.f('ix_hot_links_section_key'), table_name='hot_links')
    op.drop_index(op.f('ix_hot_links_category_id'), table_name='hot_links')
    op.drop_table('hot_links')
    op.drop_index('ix_trend_category_platform', table_name='trend_signals')
    op.drop_index(op.f('ix_trend_signals_collected_at'), table_name='trend_signals')
    op.drop_index(op.f('ix_trend_signals_platform'), table_name='trend_signals')
    op.drop_index(op.f('ix_trend_signals_signal_type'), table_name='trend_signals')
    op.drop_index(op.f('ix_trend_signals_section_key'), table_name='trend_signals')
    op.drop_index(op.f('ix_trend_signals_category_id'), table_name='trend_signals')
    op.drop_table('trend_signals')
