"""Add score justification fields to assessments

Revision ID: 20260530_000002
Revises: 20260529_000001
Create Date: 2026-05-30 11:15:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20260530_000002"
down_revision = "20260529_000001"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    bind = op.get_bind()
    return {col["name"] for col in inspect(bind).get_columns(table)}


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    if column.name not in _columns(table):
        op.add_column(table, column)


def upgrade() -> None:
    _add_column_if_missing("assessments", sa.Column("data_justification", sa.Text(), nullable=True))
    _add_column_if_missing("assessments", sa.Column("process_justification", sa.Text(), nullable=True))
    _add_column_if_missing("assessments", sa.Column("integration_justification", sa.Text(), nullable=True))
    _add_column_if_missing("assessments", sa.Column("governance_justification", sa.Text(), nullable=True))
    _add_column_if_missing("assessments", sa.Column("security_justification", sa.Text(), nullable=True))
    _add_column_if_missing("assessments", sa.Column("team_justification", sa.Text(), nullable=True))
    _add_column_if_missing("assessments", sa.Column("alignment_justification", sa.Text(), nullable=True))


def downgrade() -> None:
    cols = _columns("assessments")
    for name in (
        "alignment_justification",
        "team_justification",
        "security_justification",
        "governance_justification",
        "integration_justification",
        "process_justification",
        "data_justification",
    ):
        if name in cols:
            op.drop_column("assessments", name)
