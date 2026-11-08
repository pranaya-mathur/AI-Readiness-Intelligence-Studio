"""Phase 1 evidence provenance and scoring transparency fields

Revision ID: 20261108_000003
Revises: 20260530_000002
Create Date: 2026-11-08 14:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261108_000003"
down_revision = "20260530_000002"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    bind = op.get_bind()
    return {col["name"] for col in inspect(bind).get_columns(table)}


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    if column.name not in _columns(table):
        op.add_column(table, column)


def upgrade() -> None:
    _add_column_if_missing("assessments", sa.Column("scoring_rubric_version", sa.String(), nullable=True))
    _add_column_if_missing("assessments", sa.Column("scoring_method", sa.String(), nullable=True))
    _add_column_if_missing("assessments", sa.Column("dimension_score_details", sa.JSON(), nullable=True))
    _add_column_if_missing("assessments", sa.Column("automation_potential_basis", sa.String(), nullable=True))
    _add_column_if_missing("assessments", sa.Column("analysis_mode", sa.String(), nullable=True))
    _add_column_if_missing("assessments", sa.Column("model_provider", sa.String(), nullable=True))
    _add_column_if_missing("assessments", sa.Column("model_name", sa.String(), nullable=True))
    _add_column_if_missing("assessments", sa.Column("model_run_status", sa.String(), nullable=True))
    _add_column_if_missing("assessments", sa.Column("model_error", sa.Text(), nullable=True))
    _add_column_if_missing("assessments", sa.Column("evidence_package", sa.JSON(), nullable=True))
    _add_column_if_missing(
        "assessments",
        sa.Column("insufficient_evidence", sa.Integer(), server_default="0", nullable=True),
    )

    _add_column_if_missing("document_signals", sa.Column("document_id", sa.String(), nullable=True))
    _add_column_if_missing("document_signals", sa.Column("excerpt", sa.Text(), nullable=True))
    _add_column_if_missing("document_signals", sa.Column("page_or_section", sa.String(), nullable=True))
    _add_column_if_missing("document_signals", sa.Column("evidence_tier", sa.String(), nullable=True))
    _add_column_if_missing("document_signals", sa.Column("evidence_id", sa.String(), nullable=True))


def downgrade() -> None:
    signal_cols = _columns("document_signals")
    for name in ("evidence_id", "evidence_tier", "page_or_section", "excerpt", "document_id"):
        if name in signal_cols:
            op.drop_column("document_signals", name)

    assessment_cols = _columns("assessments")
    for name in (
        "insufficient_evidence",
        "evidence_package",
        "model_error",
        "model_run_status",
        "model_name",
        "model_provider",
        "analysis_mode",
        "automation_potential_basis",
        "dimension_score_details",
        "scoring_method",
        "scoring_rubric_version",
    ):
        if name in assessment_cols:
            op.drop_column("assessments", name)
