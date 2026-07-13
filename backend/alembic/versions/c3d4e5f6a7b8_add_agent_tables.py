"""add agent_scans, product_discoveries, agent_messages tables

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-07-12 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'agent_scans',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('scan_type', sa.String(length=40), nullable=False),
        sa.Column('category_code', sa.String(length=80), nullable=True),
        sa.Column('topic', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('triggered_by', sa.String(length=120), nullable=False),
        sa.Column('report', sa.JSON(), nullable=False),
        sa.Column('data_snapshot', sa.JSON(), nullable=False),
        sa.Column('stats', sa.JSON(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_agent_scans_scan_type'), 'agent_scans', ['scan_type'], unique=False)
    op.create_index(op.f('ix_agent_scans_category_code'), 'agent_scans', ['category_code'], unique=False)
    op.create_index(op.f('ix_agent_scans_status'), 'agent_scans', ['status'], unique=False)

    op.create_table(
        'product_discoveries',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('scan_id', sa.BigInteger(), nullable=False),
        sa.Column('product_name', sa.String(length=500), nullable=False),
        sa.Column('category_code', sa.String(length=80), nullable=True),
        sa.Column('opportunity_type', sa.String(length=40), nullable=False),
        sa.Column('opportunity_score', sa.Float(), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=False),
        sa.Column('market_signals', sa.JSON(), nullable=False),
        sa.Column('keywords', sa.JSON(), nullable=False),
        sa.Column('source_links', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('user_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['scan_id'], ['agent_scans.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_product_discoveries_scan_id'), 'product_discoveries', ['scan_id'], unique=False)
    op.create_index(op.f('ix_product_discoveries_category_code'), 'product_discoveries', ['category_code'], unique=False)
    op.create_index(op.f('ix_product_discoveries_opportunity_type'), 'product_discoveries', ['opportunity_type'], unique=False)
    op.create_index(op.f('ix_product_discoveries_status'), 'product_discoveries', ['status'], unique=False)
    op.create_index('ix_discovery_scan_opportunity', 'product_discoveries', ['scan_id', 'opportunity_type'], unique=False)

    op.create_table(
        'agent_messages',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('scan_id', sa.BigInteger(), nullable=False),
        sa.Column('role', sa.String(length=16), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['scan_id'], ['agent_scans.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_agent_messages_scan_id'), 'agent_messages', ['scan_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_agent_messages_scan_id'), table_name='agent_messages')
    op.drop_table('agent_messages')
    op.drop_index('ix_discovery_scan_opportunity', table_name='product_discoveries')
    op.drop_index(op.f('ix_product_discoveries_status'), table_name='product_discoveries')
    op.drop_index(op.f('ix_product_discoveries_opportunity_type'), table_name='product_discoveries')
    op.drop_index(op.f('ix_product_discoveries_category_code'), table_name='product_discoveries')
    op.drop_index(op.f('ix_product_discoveries_scan_id'), table_name='product_discoveries')
    op.drop_table('product_discoveries')
    op.drop_index(op.f('ix_agent_scans_status'), table_name='agent_scans')
    op.drop_index(op.f('ix_agent_scans_category_code'), table_name='agent_scans')
    op.drop_index(op.f('ix_agent_scans_scan_type'), table_name='agent_scans')
    op.drop_table('agent_scans')
