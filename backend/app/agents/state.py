from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AssessmentState(BaseModel):
    # Assessment Meta & Context
    assessment_id: int
    company_name: str
    industry: str
    company_size: str
    departments: List[str] = Field(default_factory=list)
    current_tools: List[str] = Field(default_factory=list)
    cloud_preference: str = "Cloud-agnostic"
    compliance_requirements: List[str] = Field(default_factory=list)
    main_business_goals: str = ""
    pain_points: List[str] = Field(default_factory=list)
    ai_goals: List[str] = Field(default_factory=list)

    # Document Signals / Evidence
    extracted_text: str = ""  # Consolidated text corpus (bounded)
    documents: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_package: Dict[str, Any] = Field(default_factory=dict)
    extracted_signals: List[Dict[str, Any]] = Field(default_factory=list)
    insufficient_evidence: bool = False

    # Analysis & Insights
    business_summary: str = ""
    bottlenecks: List[Dict[str, Any]] = Field(default_factory=list)
    use_cases: List[Dict[str, Any]] = Field(default_factory=list)

    # Scores
    data_readiness: float = 0.0
    data_justification: Optional[str] = None
    process_readiness: float = 0.0
    process_justification: Optional[str] = None
    integration_readiness: float = 0.0
    integration_justification: Optional[str] = None
    governance_readiness: float = 0.0
    governance_justification: Optional[str] = None
    security_readiness: float = 0.0
    security_justification: Optional[str] = None
    team_readiness: float = 0.0
    team_justification: Optional[str] = None
    business_alignment: float = 0.0
    alignment_justification: Optional[str] = None
    overall_score: float = 0.0
    automation_potential: float = 0.0
    readiness_interpretation: str = ""
    scoring_rubric_version: str = ""
    scoring_method: str = ""
    dimension_score_details: Dict[str, Any] = Field(default_factory=dict)
    automation_potential_basis: str = ""

    # Governance & Risks
    risks: List[Dict[str, Any]] = Field(default_factory=list)

    # Pilot & Strategy
    recommended_pilot: Dict[str, Any] = Field(default_factory=dict)

    # Roadmap & Outputs
    roadmap_items: List[Dict[str, Any]] = Field(default_factory=list)
    proposal_summary: Dict[str, Any] = Field(default_factory=dict)

    # Model execution transparency
    analysis_mode: str = "real"  # real | demo
    model_provider: str = "none"
    model_name: str = "none"
    model_run_status: str = "not_started"
    model_error: Optional[str] = None
    model_run_history: List[Dict[str, Any]] = Field(default_factory=list)

    # Orchestration logs / progress trackers
    logs: List[str] = Field(default_factory=list)
    current_node: str = "init"
    analysis_incomplete: bool = False
    incomplete_reason: Optional[str] = None
