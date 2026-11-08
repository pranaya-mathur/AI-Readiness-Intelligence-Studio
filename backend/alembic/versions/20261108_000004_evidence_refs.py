"""Add evidence_refs JSON columns for finding-to-evidence links

Revision ID: 20261108_000004
Revises: 20261108_000003
Create Date: 2026-11-08 15:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20261108_000004"
down_revision = "20261108_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("process_bottlenecks", sa.Column("evidence_refs", sa.JSON(), nullable=True))
    op.add_column("ai_use_cases", sa.Column("evidence_refs", sa.JSON(), nullable=True))
    op.add_column("risk_registers", sa.Column("evidence_refs", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("risk_registers", "evidence_refs")
    op.drop_column("ai_use_cases", "evidence_refs")
    op.drop_column("process_bottlenecks", "evidence_refs")
