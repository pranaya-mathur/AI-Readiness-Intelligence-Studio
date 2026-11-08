"""Phase 2 investment decision intelligence tables and assessment fields

Revision ID: 20261108_000005
Revises: 20261108_000004
Create Date: 2026-11-08 16:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261108_000005"
down_revision = "20261108_000004"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    bind = op.get_bind()
    return {col["name"] for col in inspect(bind).get_columns(table)}


def _tables() -> set[str]:
    bind = op.get_bind()
    return set(inspect(bind).get_table_names())


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    if column.name not in _columns(table):
        op.add_column(table, column)


def upgrade() -> None:
    _add_column_if_missing(
        "assessments", sa.Column("prioritization_rubric_version", sa.String(), nullable=True)
    )
    _add_column_if_missing(
        "assessments", sa.Column("financial_model_version", sa.String(), nullable=True)
    )
    _add_column_if_missing("assessments", sa.Column("investment_package", sa.JSON(), nullable=True))
    _add_column_if_missing(
        "assessments", sa.Column("investment_decision_status", sa.String(), nullable=True)
    )
    _add_column_if_missing(
        "assessments", sa.Column("investment_decision_explanation", sa.Text(), nullable=True)
    )
    _add_column_if_missing(
        "assessments",
        sa.Column("investment_decision_reviewer_id", sa.Integer(), nullable=True),
    )
    _add_column_if_missing(
        "assessments", sa.Column("investment_decision_at", sa.DateTime(), nullable=True)
    )
    _add_column_if_missing(
        "assessments", sa.Column("recommended_opportunity_id", sa.Integer(), nullable=True)
    )
    _add_column_if_missing("assessments", sa.Column("pilot_plan", sa.JSON(), nullable=True))

    if "opportunity_evaluations" not in _tables():
        op.create_table(
            "opportunity_evaluations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "assessment_id",
                sa.Integer(),
                sa.ForeignKey("assessments.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "use_case_id",
                sa.Integer(),
                sa.ForeignKey("ai_use_cases.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("department", sa.String(), nullable=True),
            sa.Column("criterion_scores", sa.JSON(), nullable=True),
            sa.Column("criterion_weights", sa.JSON(), nullable=True),
            sa.Column("original_criterion_scores", sa.JSON(), nullable=True),
            sa.Column("reviewed_criterion_scores", sa.JSON(), nullable=True),
            sa.Column("weighted_priority_score", sa.Float(), nullable=True),
            sa.Column("original_priority_score", sa.Float(), nullable=True),
            sa.Column("ranking", sa.Integer(), nullable=True),
            sa.Column("ranking_explanation", sa.Text(), nullable=True),
            sa.Column("evidence_refs", sa.JSON(), nullable=True),
            sa.Column("missing_information", sa.JSON(), nullable=True),
            sa.Column("confidence_class", sa.String(), nullable=True),
            sa.Column("recommendation_status", sa.String(), nullable=True),
            sa.Column("hard_blockers", sa.JSON(), nullable=True),
            sa.Column("is_blocked", sa.Integer(), server_default="0", nullable=True),
            sa.Column("feasibility", sa.JSON(), nullable=True),
            sa.Column("financial_inputs", sa.JSON(), nullable=True),
            sa.Column("original_financial_inputs", sa.JSON(), nullable=True),
            sa.Column("financial_evaluation", sa.JSON(), nullable=True),
            sa.Column("pilot_selected", sa.Integer(), server_default="0", nullable=True),
            sa.Column("prioritization_rubric_version", sa.String(), nullable=True),
            sa.Column("financial_model_version", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_opportunity_evaluations_id", "opportunity_evaluations", ["id"])
        op.create_index(
            "ix_opportunity_evaluations_assessment_id",
            "opportunity_evaluations",
            ["assessment_id"],
        )
        op.create_index(
            "ix_opportunity_evaluations_use_case_id",
            "opportunity_evaluations",
            ["use_case_id"],
        )

    if "investment_review_events" not in _tables():
        op.create_table(
            "investment_review_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "assessment_id",
                sa.Integer(),
                sa.ForeignKey("assessments.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("opportunity_evaluation_id", sa.Integer(), nullable=True),
            sa.Column("reviewer_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("event_type", sa.String(), nullable=False),
            sa.Column("field_name", sa.String(), nullable=True),
            sa.Column("previous_value", sa.JSON(), nullable=True),
            sa.Column("new_value", sa.JSON(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("prioritization_rubric_version", sa.String(), nullable=True),
            sa.Column("financial_model_version", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_investment_review_events_id", "investment_review_events", ["id"])
        op.create_index(
            "ix_investment_review_events_assessment_id",
            "investment_review_events",
            ["assessment_id"],
        )
        op.create_index(
            "ix_investment_review_events_opportunity_evaluation_id",
            "investment_review_events",
            ["opportunity_evaluation_id"],
        )


def downgrade() -> None:
    if "investment_review_events" in _tables():
        op.drop_table("investment_review_events")
    if "opportunity_evaluations" in _tables():
        op.drop_table("opportunity_evaluations")
    for col in (
        "pilot_plan",
        "recommended_opportunity_id",
        "investment_decision_at",
        "investment_decision_reviewer_id",
        "investment_decision_explanation",
        "investment_decision_status",
        "investment_package",
        "financial_model_version",
        "prioritization_rubric_version",
    ):
        if col in _columns("assessments"):
            op.drop_column("assessments", col)
