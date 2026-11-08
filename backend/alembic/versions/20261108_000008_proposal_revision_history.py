"""Add immutable proposal/SOW revision history on assessments.

Revision ID: 20261108_000008
Revises: 20261108_000007
Create Date: 2026-11-08
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261108_000008"
down_revision: Union[str, None] = "20261108_000007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return set()
    return {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    if "proposal_revision_history" not in _column_names("assessments"):
        op.add_column(
            "assessments",
            sa.Column("proposal_revision_history", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    if "proposal_revision_history" in _column_names("assessments"):
        op.drop_column("assessments", "proposal_revision_history")
