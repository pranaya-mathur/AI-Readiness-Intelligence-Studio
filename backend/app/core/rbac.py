"""Backend-enforced workspace roles and permissions (Phase 3)."""

from __future__ import annotations

from typing import Iterable

ROLE_OWNER_ADMIN = "owner_admin"
ROLE_CONSULTANT_ANALYST = "consultant_analyst"
ROLE_REVIEWER_APPROVER = "reviewer_approver"
ROLE_CLIENT_VIEWER = "client_viewer"

ALL_ROLES = {
    ROLE_OWNER_ADMIN,
    ROLE_CONSULTANT_ANALYST,
    ROLE_REVIEWER_APPROVER,
    ROLE_CLIENT_VIEWER,
}

WORKSPACE_ENTERPRISE = "enterprise"
WORKSPACE_CONSULTING_AGENCY = "consulting_agency"
WORKSPACE_TYPES = {WORKSPACE_ENTERPRISE, WORKSPACE_CONSULTING_AGENCY}

# Engagement / workflow statuses (assessment + client engagement).
WORKFLOW_DRAFT = "draft"
WORKFLOW_DISCOVERY = "discovery"
WORKFLOW_ASSESSMENT_COMPLETED = "assessment_completed"
WORKFLOW_CONSULTANT_REVIEW = "consultant_review"
WORKFLOW_INVESTMENT_REVIEW = "investment_review"
WORKFLOW_APPROVED = "approved"
WORKFLOW_PROPOSAL_PREPARED = "proposal_prepared"
WORKFLOW_DELIVERED = "delivered"

WORKFLOW_STATUSES = {
    WORKFLOW_DRAFT,
    WORKFLOW_DISCOVERY,
    WORKFLOW_ASSESSMENT_COMPLETED,
    WORKFLOW_CONSULTANT_REVIEW,
    WORKFLOW_INVESTMENT_REVIEW,
    WORKFLOW_APPROVED,
    WORKFLOW_PROPOSAL_PREPARED,
    WORKFLOW_DELIVERED,
}

# Permission keys
PERM_ORG_MANAGE = "org.manage"
PERM_MEMBER_MANAGE = "member.manage"
PERM_CLIENT_MANAGE = "client.manage"
PERM_ASSESSMENT_READ = "assessment.read"
PERM_ASSESSMENT_WRITE = "assessment.write"
PERM_ASSESSMENT_RUN = "assessment.run"
PERM_INVESTMENT_WRITE = "investment.write"
PERM_INVESTMENT_APPROVE = "investment.approve"
PERM_ASSESSMENT_APPROVE = "assessment.approve"
PERM_PROPOSAL_WRITE = "proposal.write"
PERM_EXPORT_APPROVED = "export.approved"
PERM_EXPORT_INTERNAL = "export.internal"
PERM_BRANDING_MANAGE = "branding.manage"
PERM_VIEW_CONSULTANT_NOTES = "notes.consultant"

ROLE_PERMISSIONS: dict[str, set[str]] = {
    ROLE_OWNER_ADMIN: {
        PERM_ORG_MANAGE,
        PERM_MEMBER_MANAGE,
        PERM_CLIENT_MANAGE,
        PERM_ASSESSMENT_READ,
        PERM_ASSESSMENT_WRITE,
        PERM_ASSESSMENT_RUN,
        PERM_INVESTMENT_WRITE,
        PERM_INVESTMENT_APPROVE,
        PERM_ASSESSMENT_APPROVE,
        PERM_PROPOSAL_WRITE,
        PERM_EXPORT_APPROVED,
        PERM_EXPORT_INTERNAL,
        PERM_BRANDING_MANAGE,
        PERM_VIEW_CONSULTANT_NOTES,
    },
    ROLE_CONSULTANT_ANALYST: {
        PERM_CLIENT_MANAGE,
        PERM_ASSESSMENT_READ,
        PERM_ASSESSMENT_WRITE,
        PERM_ASSESSMENT_RUN,
        PERM_INVESTMENT_WRITE,
        PERM_PROPOSAL_WRITE,
        PERM_EXPORT_INTERNAL,
        PERM_EXPORT_APPROVED,
        PERM_VIEW_CONSULTANT_NOTES,
    },
    # Reviewers may approve assessment/investment decisions but cannot freely
    # edit assessment content, recalculate packages, or rewrite proposals.
    ROLE_REVIEWER_APPROVER: {
        PERM_ASSESSMENT_READ,
        PERM_INVESTMENT_APPROVE,
        PERM_ASSESSMENT_APPROVE,
        PERM_EXPORT_APPROVED,
        PERM_EXPORT_INTERNAL,
        PERM_VIEW_CONSULTANT_NOTES,
    },
    ROLE_CLIENT_VIEWER: {
        PERM_ASSESSMENT_READ,
        PERM_EXPORT_APPROVED,
    },
}


def normalize_role(role: str | None) -> str:
    value = (role or "").strip().lower()
    if value not in ALL_ROLES:
        raise ValueError(f"Invalid role: {role}")
    return value


def has_permission(role: str | None, permission: str) -> bool:
    try:
        normalized = normalize_role(role)
    except ValueError:
        return False
    return permission in ROLE_PERMISSIONS.get(normalized, set())


def require_any_permission(role: str | None, permissions: Iterable[str]) -> bool:
    return any(has_permission(role, p) for p in permissions)
