"""Shared backend validation for assessment, investment, and workflow approvals."""

from __future__ import annotations

from fastapi import HTTPException

from app.models import Assessment

VALID_APPROVAL_STATUSES = {"draft", "reviewed", "approved"}
VALID_INVESTMENT_DECISIONS = {
    "invest",
    "validate_first",
    "defer",
    "not_recommended",
    "pending_review",
}

# Workflow statuses that represent client-facing approval / delivery.
CLIENT_FACING_WORKFLOWS = {"approved", "proposal_prepared", "delivered"}


def assessment_is_client_exportable(ass: Assessment) -> tuple[bool, str]:
    """Real client exports require a completed, non-demo, non-simulated analysis."""
    status = (ass.status or "").lower()
    if status in {"incomplete", "failed", "processing", "intake", "uploading"}:
        return (
            False,
            f"Assessment status '{status}' is not exportable as a verified client report",
        )
    analysis_mode = (getattr(ass, "analysis_mode", None) or "").lower()
    model_status = (getattr(ass, "model_run_status", None) or "").lower()
    if analysis_mode == "demo" or model_status in {"demo_simulated", "simulated"}:
        return (
            False,
            "Demo/simulated assessments cannot be treated as verified client deliverables",
        )
    if status != "completed":
        return False, f"Assessment status '{status}' is not completed"
    return True, ""


def assert_assessment_approvable(
    ass: Assessment, *, target_status: str = "approved"
) -> None:
    """Enforce prerequisites before assessment approval_status promotion."""
    if target_status not in {"reviewed", "approved"}:
        return
    status = (ass.status or "").lower()
    if status in {"incomplete", "failed", "intake", "uploading", "processing"}:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot approve an assessment with status '{ass.status}'. "
                "Complete analysis successfully first."
            ),
        )

    # Internal "reviewed" is allowed on demo/heuristic runs; client-facing
    # "approved" requires verified, non-demo analysis.
    if target_status == "reviewed":
        return

    exportable, reason = assessment_is_client_exportable(ass)
    analysis_mode = (getattr(ass, "analysis_mode", "") or "").lower()
    if not exportable and analysis_mode == "demo":
        raise HTTPException(
            status_code=409,
            detail=(
                "Demo/simulated assessments cannot be approved as verified "
                "client deliverables. Use internal demo export mode instead."
            ),
        )
    if (getattr(ass, "model_run_status", "") or "").lower() == "demo_simulated":
        raise HTTPException(
            status_code=409,
            detail="Simulated model output cannot be approved as verified analysis.",
        )
    if not exportable:
        raise HTTPException(
            status_code=409, detail=reason or "Assessment is not approvable"
        )


def assert_investment_decision_allowed(status: str) -> None:
    if status not in VALID_INVESTMENT_DECISIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Use one of {sorted(VALID_INVESTMENT_DECISIONS)}",
        )


def assert_workflow_transition(ass: Assessment, new_status: str) -> None:
    """Prevent workflow status changes from bypassing approval prerequisites."""
    if new_status == "approved":
        assert_assessment_approvable(ass, target_status="approved")
        if (ass.approval_status or "").lower() != "approved":
            raise HTTPException(
                status_code=409,
                detail=(
                    "Assessment approval_status must be 'approved' before "
                    "workflow can be marked approved."
                ),
            )
    if new_status == "delivered":
        if (ass.approval_status or "").lower() != "approved":
            raise HTTPException(
                status_code=409,
                detail="Cannot deliver without assessment approval_status='approved'.",
            )
        if (ass.workflow_status or "").lower() not in {
            "approved",
            "proposal_prepared",
            "delivered",
        } and not getattr(ass, "locked_for_delivery", 0):
            raise HTTPException(
                status_code=409,
                detail="Delivered requires prior approved or proposal_prepared workflow.",
            )
    if new_status == "proposal_prepared":
        if (ass.approval_status or "").lower() != "approved":
            raise HTTPException(
                status_code=409,
                detail="Proposal preparation requires assessment approval_status='approved'.",
            )
