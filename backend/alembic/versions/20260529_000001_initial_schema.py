"""Initial product schema

Revision ID: 20260529_000001
Revises:
Create Date: 2026-05-29 20:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260529_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("is_active", sa.Integer(), nullable=True, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_organizations_id", "organizations", ["id"], unique=False)
    op.create_index("ix_organizations_owner_user_id", "organizations", ["owner_user_id"], unique=False)

    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("industry", sa.String(), nullable=True),
        sa.Column("company_size", sa.String(), nullable=True),
        sa.Column("cloud_preference", sa.String(), nullable=True),
        sa.Column("compliance_requirements", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_clients_id", "clients", ["id"], unique=False)
    op.create_index("ix_clients_name", "clients", ["name"], unique=False)
    op.create_index("ix_clients_organization_id", "clients", ["organization_id"], unique=False)

    op.create_table(
        "assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=True),
        sa.Column("company_name", sa.String(), nullable=False),
        sa.Column("industry", sa.String(), nullable=True),
        sa.Column("company_size", sa.String(), nullable=True),
        sa.Column("departments", sa.JSON(), nullable=True),
        sa.Column("current_tools", sa.JSON(), nullable=True),
        sa.Column("cloud_preference", sa.String(), nullable=True),
        sa.Column("compliance_requirements", sa.JSON(), nullable=True),
        sa.Column("main_business_goals", sa.Text(), nullable=True),
        sa.Column("pain_points", sa.JSON(), nullable=True),
        sa.Column("ai_goals", sa.JSON(), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=True, server_default="0"),
        sa.Column("automation_potential", sa.Float(), nullable=True, server_default="0"),
        sa.Column("confidence_score", sa.Float(), nullable=True, server_default="0"),
        sa.Column("status", sa.String(), nullable=True, server_default="intake"),
        sa.Column("risk_level", sa.String(), nullable=True, server_default="Low"),
        sa.Column("recommended_first_pilot", sa.String(), nullable=True),
        sa.Column("why_recommended_pilot", sa.Text(), nullable=True),
        sa.Column("expected_pilot_impact", sa.Text(), nullable=True),
        sa.Column("data_readiness", sa.Float(), nullable=True, server_default="0"),
        sa.Column("process_readiness", sa.Float(), nullable=True, server_default="0"),
        sa.Column("integration_readiness", sa.Float(), nullable=True, server_default="0"),
        sa.Column("governance_readiness", sa.Float(), nullable=True, server_default="0"),
        sa.Column("security_readiness", sa.Float(), nullable=True, server_default="0"),
        sa.Column("team_readiness", sa.Float(), nullable=True, server_default="0"),
        sa.Column("business_alignment", sa.Float(), nullable=True, server_default="0"),
        sa.Column("business_summary", sa.Text(), nullable=True),
        sa.Column("readiness_interpretation", sa.Text(), nullable=True),
        sa.Column("client_summary", sa.Text(), nullable=True),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("approval_status", sa.String(), nullable=True, server_default="draft"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_assessments_id", "assessments", ["id"], unique=False)
    op.create_index("ix_assessments_user_id", "assessments", ["user_id"], unique=False)
    op.create_index("ix_assessments_client_id", "assessments", ["client_id"], unique=False)
    op.create_index("ix_assessments_company_name", "assessments", ["company_name"], unique=False)

    op.create_table(
        "process_bottlenecks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assessment_id", sa.Integer(), sa.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("department", sa.String(), nullable=False),
        sa.Column("process_name", sa.String(), nullable=False),
        sa.Column("bottleneck_description", sa.Text(), nullable=False),
        sa.Column("ai_potential", sa.String(), nullable=True, server_default="Medium"),
    )
    op.create_index("ix_process_bottlenecks_id", "process_bottlenecks", ["id"], unique=False)

    op.create_table(
        "ai_use_cases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assessment_id", sa.Integer(), sa.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("department", sa.String(), nullable=False),
        sa.Column("use_case_name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("value", sa.String(), nullable=True, server_default="High"),
        sa.Column("complexity", sa.String(), nullable=True, server_default="Medium"),
        sa.Column("risk", sa.String(), nullable=True, server_default="Low"),
        sa.Column("priority", sa.String(), nullable=True, server_default="P1"),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True, server_default="85"),
    )
    op.create_index("ix_ai_use_cases_id", "ai_use_cases", ["id"], unique=False)

    op.create_table(
        "risk_registers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assessment_id", sa.Integer(), sa.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("risk_name", sa.String(), nullable=False),
        sa.Column("severity", sa.String(), nullable=True, server_default="Medium"),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("is_control_met", sa.Integer(), nullable=True, server_default="0"),
    )
    op.create_index("ix_risk_registers_id", "risk_registers", ["id"], unique=False)

    op.create_table(
        "roadmap_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assessment_id", sa.Integer(), sa.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phase", sa.String(), nullable=False),
        sa.Column("action_item", sa.String(), nullable=False),
        sa.Column("expected_impact", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True, server_default="80"),
    )
    op.create_index("ix_roadmap_items_id", "roadmap_items", ["id"], unique=False)

    op.create_table(
        "document_signals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assessment_id", sa.Integer(), sa.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_file", sa.String(), nullable=False),
        sa.Column("signal_type", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True, server_default="90"),
    )
    op.create_index("ix_document_signals_id", "document_signals", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_document_signals_id", table_name="document_signals")
    op.drop_table("document_signals")
    op.drop_index("ix_roadmap_items_id", table_name="roadmap_items")
    op.drop_table("roadmap_items")
    op.drop_index("ix_risk_registers_id", table_name="risk_registers")
    op.drop_table("risk_registers")
    op.drop_index("ix_ai_use_cases_id", table_name="ai_use_cases")
    op.drop_table("ai_use_cases")
    op.drop_index("ix_process_bottlenecks_id", table_name="process_bottlenecks")
    op.drop_table("process_bottlenecks")
    op.drop_index("ix_assessments_company_name", table_name="assessments")
    op.drop_index("ix_assessments_client_id", table_name="assessments")
    op.drop_index("ix_assessments_user_id", table_name="assessments")
    op.drop_index("ix_assessments_id", table_name="assessments")
    op.drop_table("assessments")
    op.drop_index("ix_clients_organization_id", table_name="clients")
    op.drop_index("ix_clients_name", table_name="clients")
    op.drop_index("ix_clients_id", table_name="clients")
    op.drop_table("clients")
    op.drop_index("ix_organizations_owner_user_id", table_name="organizations")
    op.drop_index("ix_organizations_id", table_name="organizations")
    op.drop_table("organizations")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
