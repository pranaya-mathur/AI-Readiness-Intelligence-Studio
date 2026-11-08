"""Phase 1 evidence provenance and scoring transparency fields

Revision ID: 20261108_000003
Revises: 20260530_000002
Create Date: 2026-11-08 14:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20261108_000003"
down_revision = "20260530_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assessments", sa.Column("scoring_rubric_version", sa.String(), nullable=True))
    op.add_column("assessments", sa.Column("scoring_method", sa.String(), nullable=True))
    op.add_column("assessments", sa.Column("dimension_score_details", sa.JSON(), nullable=True))
    op.add_column("assessments", sa.Column("automation_potential_basis", sa.String(), nullable=True))
    op.add_column("assessments", sa.Column("analysis_mode", sa.String(), nullable=True))
    op.add_column("assessments", sa.Column("model_provider", sa.String(), nullable=True))
    op.add_column("assessments", sa.Column("model_name", sa.String(), nullable=True))
    op.add_column("assessments", sa.Column("model_run_status", sa.String(), nullable=True))
    op.add_column("assessments", sa.Column("model_error", sa.Text(), nullable=True))
    op.add_column("assessments", sa.Column("evidence_package", sa.JSON(), nullable=True))
    op.add_column(
        "assessments",
        sa.Column("insufficient_evidence", sa.Integer(), server_default="0", nullable=True),
    )

    op.add_column("document_signals", sa.Column("document_id", sa.String(), nullable=True))
    op.add_column("document_signals", sa.Column("excerpt", sa.Text(), nullable=True))
    op.add_column("document_signals", sa.Column("page_or_section", sa.String(), nullable=True))
    op.add_column("document_signals", sa.Column("evidence_tier", sa.String(), nullable=True))
    op.add_column("document_signals", sa.Column("evidence_id", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("document_signals", "evidence_id")
    op.drop_column("document_signals", "evidence_tier")
    op.drop_column("document_signals", "page_or_section")
    op.drop_column("document_signals", "excerpt")
    op.drop_column("document_signals", "document_id")

    op.drop_column("assessments", "insufficient_evidence")
    op.drop_column("assessments", "evidence_package")
    op.drop_column("assessments", "model_error")
    op.drop_column("assessments", "model_run_status")
    op.drop_column("assessments", "model_name")
    op.drop_column("assessments", "model_provider")
    op.drop_column("assessments", "analysis_mode")
    op.drop_column("assessments", "automation_potential_basis")
    op.drop_column("assessments", "dimension_score_details")
    op.drop_column("assessments", "scoring_method")
    op.drop_column("assessments", "scoring_rubric_version")
