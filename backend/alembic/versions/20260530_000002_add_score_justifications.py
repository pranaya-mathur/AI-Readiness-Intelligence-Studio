"""Add score justification fields to assessments

Revision ID: 20260530_000002
Revises: 20260529_000001
Create Date: 2026-05-30 11:15:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260530_000002"
down_revision = "20260529_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assessments", sa.Column("data_justification", sa.Text(), nullable=True))
    op.add_column("assessments", sa.Column("process_justification", sa.Text(), nullable=True))
    op.add_column("assessments", sa.Column("integration_justification", sa.Text(), nullable=True))
    op.add_column("assessments", sa.Column("governance_justification", sa.Text(), nullable=True))
    op.add_column("assessments", sa.Column("security_justification", sa.Text(), nullable=True))
    op.add_column("assessments", sa.Column("team_justification", sa.Text(), nullable=True))
    op.add_column("assessments", sa.Column("alignment_justification", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("assessments", "alignment_justification")
    op.drop_column("assessments", "team_justification")
    op.drop_column("assessments", "security_justification")
    op.drop_column("assessments", "governance_justification")
    op.drop_column("assessments", "integration_justification")
    op.drop_column("assessments", "process_justification")
    op.drop_column("assessments", "data_justification")
