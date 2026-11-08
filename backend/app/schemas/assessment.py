from datetime import datetime

from pydantic import BaseModel, EmailStr


# --- Auth Schemas ---
class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    is_active: int
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str | None = None


# --- Assessment Support Schemas ---
class BottleneckBase(BaseModel):
    department: str
    process_name: str
    bottleneck_description: str
    ai_potential: str
    evidence_refs: list[str] | None = None


class BottleneckCreate(BottleneckBase):
    pass


class BottleneckResponse(BottleneckBase):
    id: int
    assessment_id: int

    class Config:
        from_attributes = True


class UseCaseBase(BaseModel):
    department: str
    use_case_name: str
    description: str
    value: str
    complexity: str
    risk: str
    priority: str
    evidence: str | None = None
    confidence: float = 85.0
    evidence_refs: list[str] | None = None


class UseCaseCreate(UseCaseBase):
    pass


class UseCaseResponse(UseCaseBase):
    id: int
    assessment_id: int

    class Config:
        from_attributes = True


class RiskBase(BaseModel):
    risk_name: str
    severity: str
    recommendation: str
    is_control_met: int = 0
    evidence_refs: list[str] | None = None


class RiskCreate(RiskBase):
    pass


class RiskResponse(RiskBase):
    id: int
    assessment_id: int

    class Config:
        from_attributes = True


class RoadmapBase(BaseModel):
    phase: str
    action_item: str
    expected_impact: str
    confidence: float = 80.0


class RoadmapCreate(RoadmapBase):
    pass


class RoadmapResponse(RoadmapBase):
    id: int
    assessment_id: int

    class Config:
        from_attributes = True


class SignalBase(BaseModel):
    source_file: str
    signal_type: str
    description: str
    confidence: float = 0.0
    document_id: str | None = None
    excerpt: str | None = None
    page_or_section: str | None = None
    evidence_tier: str | None = None
    evidence_id: str | None = None


class SignalResponse(SignalBase):
    id: int
    assessment_id: int

    class Config:
        from_attributes = True


class ClientBase(BaseModel):
    name: str
    industry: str | None = None
    company_size: str | None = None
    cloud_preference: str | None = None
    compliance_requirements: list[str] = []


class ClientCreate(ClientBase):
    pass


class ClientResponse(ClientBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Main Assessment Schemas ---
class AssessmentCreate(BaseModel):
    client_id: int | None = None
    organization_id: int | None = None
    company_name: str
    industry: str | None = "Professional Services"
    company_size: str | None = "100-500 employees"
    departments: list[str] = []
    current_tools: list[str] = []
    cloud_preference: str | None = "Cloud-agnostic"
    compliance_requirements: list[str] = []
    main_business_goals: str | None = ""
    pain_points: list[str] = []
    ai_goals: list[str] = []


class AssessmentUpdate(BaseModel):
    # Allows Human Review Mode overrides
    client_id: int | None = None
    company_name: str | None = None
    industry: str | None = None
    company_size: str | None = None
    overall_score: float | None = None
    automation_potential: float | None = None
    confidence_score: float | None = None
    risk_level: str | None = None
    status: str | None = None

    # Custom score overrides
    data_readiness: float | None = None
    data_justification: str | None = None
    process_readiness: float | None = None
    process_justification: str | None = None
    integration_readiness: float | None = None
    integration_justification: str | None = None
    governance_readiness: float | None = None
    governance_justification: str | None = None
    security_readiness: float | None = None
    security_justification: str | None = None
    team_readiness: float | None = None
    team_justification: str | None = None
    business_alignment: float | None = None
    alignment_justification: str | None = None

    # Interpretation text overrides
    business_summary: str | None = None
    readiness_interpretation: str | None = None
    client_summary: str | None = None
    reviewer_notes: str | None = None
    approval_status: str | None = None
    recommended_first_pilot: str | None = None
    why_recommended_pilot: str | None = None
    expected_pilot_impact: str | None = None

    # Overriding sub-relations
    use_cases: list[UseCaseBase] | None = None
    bottlenecks: list[BottleneckBase] | None = None
    risks: list[RiskBase] | None = None
    roadmap_items: list[RoadmapBase] | None = None


class AssessmentResponse(BaseModel):
    id: int
    client_id: int | None
    organization_id: int | None = None
    business_unit: str | None = None
    workflow_status: str | None = None
    locked_for_delivery: int | None = 0
    company_name: str
    industry: str | None
    company_size: str | None
    departments: list[str] | None
    current_tools: list[str] | None
    cloud_preference: str | None
    compliance_requirements: list[str] | None
    main_business_goals: str | None
    pain_points: list[str] | None
    ai_goals: list[str] | None

    overall_score: float
    automation_potential: float
    confidence_score: float
    status: str
    risk_level: str
    recommended_first_pilot: str | None
    why_recommended_pilot: str | None
    expected_pilot_impact: str | None

    data_readiness: float
    data_justification: str | None
    process_readiness: float
    process_justification: str | None
    integration_readiness: float
    integration_justification: str | None
    governance_readiness: float
    governance_justification: str | None
    security_readiness: float
    security_justification: str | None
    team_readiness: float
    team_justification: str | None
    business_alignment: float
    alignment_justification: str | None

    business_summary: str | None
    readiness_interpretation: str | None
    client_summary: str | None
    reviewer_notes: str | None
    approval_status: str | None

    scoring_rubric_version: str | None = None
    scoring_method: str | None = None
    dimension_score_details: dict | None = None
    automation_potential_basis: str | None = None
    analysis_mode: str | None = None
    model_provider: str | None = None
    model_name: str | None = None
    model_run_status: str | None = None
    model_error: str | None = None
    evidence_package: dict | None = None
    insufficient_evidence: int | None = 0

    # Phase 2 investment intelligence (additive, optional)
    prioritization_rubric_version: str | None = None
    financial_model_version: str | None = None
    investment_decision_status: str | None = None
    investment_decision_explanation: str | None = None
    recommended_opportunity_id: int | None = None
    pilot_plan: dict | None = None
    investment_package: dict | None = None

    created_at: datetime
    updated_at: datetime

    bottlenecks: list[BottleneckResponse] = []
    use_cases: list[UseCaseResponse] = []
    risks: list[RiskResponse] = []
    roadmap_items: list[RoadmapResponse] = []
    extracted_signals: list[SignalResponse] = []
    client: ClientResponse | None = None

    class Config:
        from_attributes = True
