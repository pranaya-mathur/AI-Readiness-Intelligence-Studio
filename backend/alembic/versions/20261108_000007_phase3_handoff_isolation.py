"""Phase 3 handoff: client viewer scope + assessment-bound proposals.

Revision ID: 20261108_000007
Revises: 20261108_000006
Create Date: 2026-11-08
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.orm import Session

revision: str = "20261108_000007"
down_revision: Union[str, None] = "20261108_000006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return set()
    return {c["name"] for c in inspector.get_columns(table)}


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    if column.name not in _column_names(table):
        op.add_column(table, column)


def upgrade() -> None:
    _add_column_if_missing(
        "organization_memberships",
        sa.Column("authorized_client_ids", sa.JSON(), nullable=True),
    )
    for col in (
        sa.Column("proposal_package", sa.JSON(), nullable=True),
        sa.Column("sow_package", sa.JSON(), nullable=True),
        sa.Column("fee_estimate", sa.JSON(), nullable=True),
        sa.Column("proposal_locked", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("proposal_approved_at", sa.DateTime(), nullable=True),
    ):
        _add_column_if_missing("assessments", col)

    # Soft backfill via ORM so JSON works on SQLite and Postgres.
    bind = op.get_bind()
    session = Session(bind=bind)
    try:
        clients = session.execute(
            sa.text(
                "SELECT id, proposal_package, sow_package, fee_estimate FROM clients"
            )
        ).mappings().all()
        for row in clients:
            proposal = row["proposal_package"]
            sow = row["sow_package"]
            fee = row["fee_estimate"]
            if not proposal and not sow:
                continue
            assessment_ids = [
                r[0]
                for r in session.execute(
                    sa.text(
                        "SELECT id FROM assessments WHERE client_id = :cid ORDER BY id"
                    ),
                    {"cid": row["id"]},
                ).fetchall()
            ]
            if len(assessment_ids) != 1:
                continue
            aid = assessment_ids[0]
            existing = session.execute(
                sa.text("SELECT proposal_package FROM assessments WHERE id = :aid"),
                {"aid": aid},
            ).scalar()
            if existing:
                continue
            proposal_obj = dict(proposal) if isinstance(proposal, dict) else proposal
            sow_obj = dict(sow) if isinstance(sow, dict) else sow
            if isinstance(proposal_obj, dict):
                proposal_obj.setdefault("assessment_id", aid)
            if isinstance(sow_obj, dict):
                sow_obj.setdefault("assessment_id", aid)
            session.execute(
                sa.text(
                    "UPDATE assessments SET proposal_package = :p, sow_package = :s, "
                    "fee_estimate = :f WHERE id = :aid"
                ),
                {"p": proposal_obj, "s": sow_obj, "f": fee, "aid": aid},
            )
        session.commit()
    finally:
        session.close()


def downgrade() -> None:
    for col in (
        "proposal_approved_at",
        "proposal_locked",
        "fee_estimate",
        "sow_package",
        "proposal_package",
    ):
        if col in _column_names("assessments"):
            op.drop_column("assessments", col)
    if "authorized_client_ids" in _column_names("organization_memberships"):
        op.drop_column("organization_memberships", "authorized_client_ids")
