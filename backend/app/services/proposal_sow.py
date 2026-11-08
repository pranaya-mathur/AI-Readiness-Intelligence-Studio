"""Evidence-grounded proposal and SOW draft generation (Phase 3).

Separates estimated client benefits/ROI from proposed project fees.
Never auto-sets selling price from ROI.
"""

from __future__ import annotations

from typing import Any

PROPOSAL_PACKAGE_VERSION = "v1.0.0"
SOW_PACKAGE_VERSION = "v1.0.0"


def _incomplete(message: str) -> dict[str, Any]:
    return {"complete": False, "message": message}


def build_proposal_and_sow(
    *,
    organization: dict[str, Any],
    client: dict[str, Any],
    assessment: dict[str, Any],
    opportunity: dict[str, Any] | None,
    pilot: dict[str, Any] | None,
    fee_estimate: dict[str, Any] | None,
    branding: dict[str, Any] | None,
) -> dict[str, Any]:
    finance = (opportunity or {}).get("financial_evaluation") or {}
    base = (finance.get("scenarios") or {}).get("base") or {}
    feasibility = (opportunity or {}).get("feasibility") or {}
    fee = fee_estimate or client.get("fee_estimate") or {}

    client_benefit = {
        "evaluation_complete": bool(finance.get("evaluation_complete")),
        "currency": finance.get("currency"),
        "modeled_roi_percentage": base.get("roi_percentage"),
        "modeled_payback_months": base.get("payback_months"),
        "modeled_net_annual_savings": base.get("net_annual_savings"),
        "modeled_implementation_investment": base.get("implementation_investment"),
        "illustrative": bool(finance.get("illustrative")),
        "disclaimer": (
            "Modeled client benefits are not the proposed project fee. "
            "ROI projections require validated baselines and are not commercial quotes."
        ),
    }
    if not client_benefit["evaluation_complete"]:
        client_benefit["status"] = _incomplete(
            finance.get("incomplete_message")
            or "Financial evaluation incomplete — additional baseline information required."
        )

    project_fees = {
        "currency": fee.get("currency") or finance.get("currency") or "USD",
        "discovery_fee": fee.get("discovery_fee"),
        "pilot_fee": fee.get("pilot_fee"),
        "implementation_fee": fee.get("implementation_fee"),
        "monthly_retainer": fee.get("monthly_retainer"),
        "assumptions": fee.get("assumptions") or [],
        "complete": bool(
            fee.get("pilot_fee") is not None
            or fee.get("implementation_fee") is not None
        ),
    }
    if not project_fees["complete"]:
        project_fees["status"] = _incomplete(
            "Proposed project fees incomplete — enter explicit commercial estimates. "
            "Do not use ROI savings as the selling price."
        )

    operating_costs = {
        "cloud_llm_monthly_cost": (
            (opportunity or {}).get("financial_inputs") or {}
        ).get("cloud_llm_monthly_cost"),
        "licensing_monthly_cost": (
            (opportunity or {}).get("financial_inputs") or {}
        ).get("licensing_monthly_cost"),
        "support_monthly_cost": ((opportunity or {}).get("financial_inputs") or {}).get(
            "support_monthly_cost"
        ),
        "disclaimer": "Operating costs are client-run estimates, separate from agency fees.",
    }

    recommended_name = (
        (opportunity or {}).get("use_case_name")
        or (opportunity or {}).get("name")
        or (pilot or {}).get("opportunity_name")
        or assessment.get("recommended_first_pilot")
        or "Recommended AI opportunity (pending selection)"
    )

    missing: list[str] = []
    if not opportunity:
        missing.append("No selected opportunity evaluation")
    if not project_fees["complete"]:
        missing.append("Proposed project fees incomplete")
    if not client_benefit["evaluation_complete"]:
        missing.append("Client benefit/ROI model incomplete")
    if not feasibility.get("proposed_approach"):
        missing.append("Technical approach not evidenced")

    stages = (pilot or {}).get("stages") or []
    milestones = []
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        milestones.append(
            {
                "name": stage.get("name"),
                "objective": stage.get("objective"),
                "deliverables": stage.get("deliverables") or [],
                "acceptance_criteria": stage.get("acceptance_criteria") or [],
                "estimated_effort_range": stage.get("estimated_effort_range"),
                "decision_gate": stage.get("decision_gate"),
            }
        )

    proposal = {
        "package_version": PROPOSAL_PACKAGE_VERSION,
        "branding": branding or {},
        "client_context": {
            "client_name": client.get("name") or assessment.get("company_name"),
            "industry": client.get("industry") or assessment.get("industry"),
            "business_unit": client.get("business_unit")
            or assessment.get("business_unit"),
            "problem_statement": assessment.get("main_business_goals")
            or assessment.get("client_summary")
            or assessment.get("business_summary"),
            "pain_points": assessment.get("pain_points") or [],
        },
        "recommended_opportunity": {
            "name": recommended_name,
            "description": (opportunity or {}).get("description"),
            "ranking": (opportunity or {}).get("ranking"),
            "priority_score": (opportunity or {}).get("weighted_priority_score"),
            "selection_rationale": (pilot or {}).get("selection_rationale")
            or assessment.get("why_recommended_pilot"),
        },
        "proposed_solution_approach": {
            "approach": feasibility.get("proposed_approach"),
            "rationale": feasibility.get("approach_rationale"),
            "human_in_the_loop_required": feasibility.get("human_in_the_loop_required"),
            "prerequisites": feasibility.get("prerequisites") or [],
            "dependencies": feasibility.get("dependencies") or [],
            "constraints": feasibility.get("known_constraints") or [],
        },
        "client_benefit_model": client_benefit,
        "proposed_project_fees": project_fees,
        "operating_cost_estimates": operating_costs,
        "pilot_success_criteria": (pilot or {}).get("success_metrics") or [],
        "out_of_scope": [
            "Unbounded enterprise automation without pilot evaluation",
            "Guaranteed ROI or fixed accuracy claims without measured baselines",
            "Production scale-out before pilot decision gate",
        ],
        "missing_information": missing,
        "approval": {
            "assessment_approval_status": assessment.get("approval_status"),
            "investment_decision_status": assessment.get("investment_decision_status"),
            "workflow_status": assessment.get("workflow_status"),
        },
    }

    sow = {
        "package_version": SOW_PACKAGE_VERSION,
        "branding": branding or {},
        "parties": {
            "provider": branding.get("display_name")
            if branding
            else organization.get("name"),
            "client": client.get("name") or assessment.get("company_name"),
            "contact_email": (branding or {}).get("contact_email"),
            "contact_phone": (branding or {}).get("contact_phone"),
        },
        "scope": {
            "opportunity": recommended_name,
            "deliverables": [
                "Discovery and baseline validation worksheet",
                "Constrained proof-of-concept with human review",
                "Pilot evaluation report against agreed success criteria",
                "Decision record for scale / defer / stop",
            ],
            "out_of_scope": proposal["out_of_scope"],
        },
        "technical_dependencies": feasibility.get("dependencies") or [],
        "data_security_responsibilities": {
            "provider": [
                "Apply agreed data-handling controls for any model processing",
                "Keep audit logs for pilot outputs and reviewer actions",
            ],
            "client": [
                "Provide authorized sample data and system access",
                "Designate operational owner and reviewers",
                "Confirm compliance constraints in writing before production use",
            ],
        },
        "proposed_team_roles": [
            {
                "role": "Engagement lead",
                "responsibility": "Scope, timeline, decision gates",
            },
            {
                "role": "Solution architect",
                "responsibility": "Approach and integration design",
            },
            {
                "role": "Domain reviewer",
                "responsibility": "Human-in-the-loop quality and acceptance",
            },
        ],
        "timeline_assumptions": [
            "Durations are ranges until discovery confirms scope and access",
            "No fixed delivery date is promised without validated dependencies",
        ],
        "milestones": milestones,
        "project_estimates": project_fees,
        "project_risks": feasibility.get("major_risks") or [],
        "client_dependencies": feasibility.get("prerequisites") or [],
        "exclusions": proposal["out_of_scope"],
        "commercial_assumptions": project_fees.get("assumptions") or [],
        "missing_information": missing,
        "footer": (branding or {}).get("footer_text"),
    }

    return {
        "proposal_package": proposal,
        "sow_package": sow,
        "complete": len(missing) == 0,
        "missing_information": missing,
    }
