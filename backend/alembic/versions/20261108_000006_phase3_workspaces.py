"""Phase 3 workspaces, memberships, branding, engagement fields

Revision ID: 20261108_000006
Revises: 20261108_000005
Create Date: 2026-11-08 17:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261108_000006"
down_revision = "20261108_000005"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    bind = op.get_bind()
    return {col["name"] for col in inspect(bind).get_columns(table)}


def _tables() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    if column.name not in _columns(table):
        op.add_column(table, column)


def upgrade() -> None:
    _add_column_if_missing("users", sa.Column("full_name", sa.String(), nullable=True))

    _add_column_if_missing(
        "organizations",
        sa.Column("workspace_type", sa.String(), nullable=True, server_default="consulting_agency"),
    )
    _add_column_if_missing(
        "organizations", sa.Column("brand_display_name", sa.String(), nullable=True)
    )
    _add_column_if_missing(
        "organizations", sa.Column("brand_logo_url", sa.String(), nullable=True)
    )
    _add_column_if_missing(
        "organizations", sa.Column("brand_primary_color", sa.String(), nullable=True)
    )
    _add_column_if_missing(
        "organizations", sa.Column("brand_secondary_color", sa.String(), nullable=True)
    )
    _add_column_if_missing(
        "organizations", sa.Column("brand_contact_email", sa.String(), nullable=True)
    )
    _add_column_if_missing(
        "organizations", sa.Column("brand_contact_phone", sa.String(), nullable=True)
    )
    _add_column_if_missing(
        "organizations", sa.Column("brand_footer_text", sa.Text(), nullable=True)
    )
    _add_column_if_missing(
        "organizations", sa.Column("updated_at", sa.DateTime(), nullable=True)
    )

    _add_column_if_missing("clients", sa.Column("business_unit", sa.String(), nullable=True))
    _add_column_if_missing(
        "clients",
        sa.Column("engagement_status", sa.String(), nullable=True, server_default="draft"),
    )
    _add_column_if_missing(
        "clients", sa.Column("assigned_consultant_user_id", sa.Integer(), nullable=True)
    )
    _add_column_if_missing("clients", sa.Column("consultant_notes", sa.Text(), nullable=True))
    _add_column_if_missing("clients", sa.Column("proposal_package", sa.JSON(), nullable=True))
    _add_column_if_missing("clients", sa.Column("sow_package", sa.JSON(), nullable=True))
    _add_column_if_missing("clients", sa.Column("fee_estimate", sa.JSON(), nullable=True))

    _add_column_if_missing(
        "assessments", sa.Column("organization_id", sa.Integer(), nullable=True)
    )
    _add_column_if_missing(
        "assessments", sa.Column("business_unit", sa.String(), nullable=True)
    )
    _add_column_if_missing(
        "assessments",
        sa.Column("workflow_status", sa.String(), nullable=True, server_default="draft"),
    )
    _add_column_if_missing(
        "assessments",
        sa.Column("locked_for_delivery", sa.Integer(), nullable=True, server_default="0"),
    )
    _add_column_if_missing(
        "assessments", sa.Column("workflow_approved_at", sa.DateTime(), nullable=True)
    )
    _add_column_if_missing(
        "assessments",
        sa.Column("workflow_approved_by_user_id", sa.Integer(), nullable=True),
    )

    if "organization_memberships" not in _tables():
        op.create_table(
            "organization_memberships",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "organization_id",
                sa.Integer(),
                sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("role", sa.String(), nullable=False, server_default="consultant_analyst"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint(
                "organization_id", "user_id", name="uq_org_membership_org_user"
            ),
        )
        op.create_index(
            "ix_organization_memberships_id", "organization_memberships", ["id"]
        )
        op.create_index(
            "ix_organization_memberships_organization_id",
            "organization_memberships",
            ["organization_id"],
        )
        op.create_index(
            "ix_organization_memberships_user_id",
            "organization_memberships",
            ["user_id"],
        )

    # Backward-compatible backfill (dialect-safe).
    conn = op.get_bind()
    orgs = conn.execute(
        sa.text("SELECT id, owner_user_id, name, workspace_type, brand_display_name FROM organizations")
    ).fetchall()
    for org in orgs:
        org_id, owner_id, name, workspace_type, brand_name = org
        exists = conn.execute(
            sa.text(
                "SELECT 1 FROM organization_memberships "
                "WHERE organization_id = :oid AND user_id = :uid"
            ),
            {"oid": org_id, "uid": owner_id},
        ).fetchone()
        if not exists:
            conn.execute(
                sa.text(
                    "INSERT INTO organization_memberships "
                    "(organization_id, user_id, role, created_at, updated_at) "
                    "VALUES (:oid, :uid, 'owner_admin', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {"oid": org_id, "uid": owner_id},
            )
        conn.execute(
            sa.text(
                "UPDATE organizations SET workspace_type = :wt, brand_display_name = :bd "
                "WHERE id = :oid"
            ),
            {
                "wt": workspace_type or "consulting_agency",
                "bd": brand_name or name,
                "oid": org_id,
            },
        )

    clients = conn.execute(
        sa.text("SELECT id, organization_id, engagement_status FROM clients")
    ).fetchall()
    for client_id, organization_id, engagement_status in clients:
        conn.execute(
            sa.text(
                "UPDATE clients SET engagement_status = :st WHERE id = :cid"
            ),
            {"st": engagement_status or "draft", "cid": client_id},
        )
        conn.execute(
            sa.text(
                "UPDATE assessments SET organization_id = :oid "
                "WHERE client_id = :cid AND organization_id IS NULL"
            ),
            {"oid": organization_id, "cid": client_id},
        )

    assessments = conn.execute(
        sa.text("SELECT id, workflow_status, locked_for_delivery FROM assessments")
    ).fetchall()
    for assessment_id, workflow_status, locked in assessments:
        conn.execute(
            sa.text(
                "UPDATE assessments SET workflow_status = :ws, "
                "locked_for_delivery = :lk WHERE id = :aid"
            ),
            {
                "ws": workflow_status or "draft",
                "lk": 0 if locked is None else locked,
                "aid": assessment_id,
            },
        )


def downgrade() -> None:
    if "organization_memberships" in _tables():
        op.drop_table("organization_memberships")
    for col in (
        "workflow_approved_by_user_id",
        "workflow_approved_at",
        "locked_for_delivery",
        "workflow_status",
        "business_unit",
        "organization_id",
    ):
        if col in _columns("assessments"):
            op.drop_column("assessments", col)
    for col in (
        "fee_estimate",
        "sow_package",
        "proposal_package",
        "consultant_notes",
        "assigned_consultant_user_id",
        "engagement_status",
        "business_unit",
    ):
        if col in _columns("clients"):
            op.drop_column("clients", col)
    for col in (
        "updated_at",
        "brand_footer_text",
        "brand_contact_phone",
        "brand_contact_email",
        "brand_secondary_color",
        "brand_primary_color",
        "brand_logo_url",
        "brand_display_name",
        "workspace_type",
    ):
        if col in _columns("organizations"):
            op.drop_column("organizations", col)
    if "full_name" in _columns("users"):
        op.drop_column("users", "full_name")
