from typing import Any

from pydantic import BaseModel, Field


class AssessmentState(BaseModel):
    # Assessment Meta & Context
    assessment_id: int
    company_name: str
    industry: str
    company_size: str
    departments: list[str] = Field(default_factory=list)
    current_tools: list[str] = Field(default_factory=list)
    cloud_preference: str = "Cloud-agnostic"
    compliance_requirements: list[str] = Field(default_factory=list)
    main_business_goals: str = ""
    pain_points: list[str] = Field(default_factory=list)
    ai_goals: list[str] = Field(default_factory=list)

    # Document Signals / Evidence
    extracted_text: str = ""  # Consolidated text corpus (bounded)
    documents: list[dict[str, Any]] = Field(default_factory=list)
    evidence_package: dict[str, Any] = Field(default_factory=dict)
    extracted_signals: list[dict[str, Any]] = Field(default_factory=list)
    insufficient_evidence: bool = False

    # Analysis & Insights
    business_summary: str = ""
    bottlenecks: list[dict[str, Any]] = Field(default_factory=list)
    use_cases: list[dict[str, Any]] = Field(default_factory=list)

    # Scores
    data_readiness: float = 0.0
    data_justification: str | None = None
    process_readiness: float = 0.0
    process_justification: str | None = None
    integration_readiness: float = 0.0
    integration_justification: str | None = None
    governance_readiness: float = 0.0
    governance_justification: str | None = None
    security_readiness: float = 0.0
    security_justification: str | None = None
    team_readiness: float = 0.0
    team_justification: str | None = None
    business_alignment: float = 0.0
    alignment_justification: str | None = None
    overall_score: float = 0.0
    automation_potential: float = 0.0
    readiness_interpretation: str = ""
    scoring_rubric_version: str = ""
    scoring_method: str = ""
    dimension_score_details: dict[str, Any] = Field(default_factory=dict)
    automation_potential_basis: str = ""

    # Governance & Risks
    risks: list[dict[str, Any]] = Field(default_factory=list)

    # Pilot & Strategy
    recommended_pilot: dict[str, Any] = Field(default_factory=dict)

    # Roadmap & Outputs
    roadmap_items: list[dict[str, Any]] = Field(default_factory=list)
    proposal_summary: dict[str, Any] = Field(default_factory=dict)

    # Model execution transparency
    analysis_mode: str = "real"  # real | demo
    model_provider: str = "none"
    model_name: str = "none"
    model_run_status: str = "not_started"
    model_error: str | None = None
    model_run_history: list[dict[str, Any]] = Field(default_factory=list)

    # Orchestration logs / progress trackers
    logs: list[str] = Field(default_factory=list)
    current_node: str = "init"
    analysis_incomplete: bool = False
    incomplete_reason: str | None = None
