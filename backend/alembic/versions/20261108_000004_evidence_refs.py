"""Add evidence_refs JSON columns for finding-to-evidence links

Revision ID: 20261108_000004
Revises: 20261108_000003
Create Date: 2026-11-08 15:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261108_000004"
down_revision = "20261108_000003"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    bind = op.get_bind()
    return {col["name"] for col in inspect(bind).get_columns(table)}


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    if column.name not in _columns(table):
        op.add_column(table, column)


def upgrade() -> None:
    _add_column_if_missing("process_bottlenecks", sa.Column("evidence_refs", sa.JSON(), nullable=True))
    _add_column_if_missing("ai_use_cases", sa.Column("evidence_refs", sa.JSON(), nullable=True))
    _add_column_if_missing("risk_registers", sa.Column("evidence_refs", sa.JSON(), nullable=True))


def downgrade() -> None:
    for table in ("risk_registers", "ai_use_cases", "process_bottlenecks"):
        if "evidence_refs" in _columns(table):
            op.drop_column(table, "evidence_refs")
