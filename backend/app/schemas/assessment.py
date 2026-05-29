from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr
from datetime import datetime

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
    email: Optional[str] = None


# --- Assessment Support Schemas ---
class BottleneckBase(BaseModel):
    department: str
    process_name: str
    bottleneck_description: str
    ai_potential: str

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
    evidence: Optional[str] = None
    confidence: float = 85.0

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
    confidence: float = 90.0

class SignalResponse(SignalBase):
    id: int
    assessment_id: int

    class Config:
        from_attributes = True

class ClientBase(BaseModel):
    name: str
    industry: Optional[str] = None
    company_size: Optional[str] = None
    cloud_preference: Optional[str] = None
    compliance_requirements: List[str] = []

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
    client_id: Optional[int] = None
    company_name: str
    industry: Optional[str] = "Professional Services"
    company_size: Optional[str] = "100-500 employees"
    departments: List[str] = []
    current_tools: List[str] = []
    cloud_preference: Optional[str] = "Cloud-agnostic"
    compliance_requirements: List[str] = []
    main_business_goals: Optional[str] = ""
    pain_points: List[str] = []
    ai_goals: List[str] = []

class AssessmentUpdate(BaseModel):
    # Allows Human Review Mode overrides
    client_id: Optional[int] = None
    company_name: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    overall_score: Optional[float] = None
    automation_potential: Optional[float] = None
    confidence_score: Optional[float] = None
    risk_level: Optional[str] = None
    status: Optional[str] = None
    
    # Custom score overrides
    data_readiness: Optional[float] = None
    process_readiness: Optional[float] = None
    integration_readiness: Optional[float] = None
    governance_readiness: Optional[float] = None
    security_readiness: Optional[float] = None
    team_readiness: Optional[float] = None
    business_alignment: Optional[float] = None
    
    # Interpretation text overrides
    business_summary: Optional[str] = None
    readiness_interpretation: Optional[str] = None
    client_summary: Optional[str] = None
    reviewer_notes: Optional[str] = None
    approval_status: Optional[str] = None
    recommended_first_pilot: Optional[str] = None
    why_recommended_pilot: Optional[str] = None
    expected_pilot_impact: Optional[str] = None

    # Overriding sub-relations
    use_cases: Optional[List[UseCaseBase]] = None
    bottlenecks: Optional[List[BottleneckBase]] = None
    risks: Optional[List[RiskBase]] = None
    roadmap_items: Optional[List[RoadmapBase]] = None

class AssessmentResponse(BaseModel):
    id: int
    client_id: Optional[int]
    company_name: str
    industry: Optional[str]
    company_size: Optional[str]
    departments: Optional[List[str]]
    current_tools: Optional[List[str]]
    cloud_preference: Optional[str]
    compliance_requirements: Optional[List[str]]
    main_business_goals: Optional[str]
    pain_points: Optional[List[str]]
    ai_goals: Optional[List[str]]
    
    overall_score: float
    automation_potential: float
    confidence_score: float
    status: str
    risk_level: str
    recommended_first_pilot: Optional[str]
    why_recommended_pilot: Optional[str]
    expected_pilot_impact: Optional[str]
    
    data_readiness: float
    process_readiness: float
    integration_readiness: float
    governance_readiness: float
    security_readiness: float
    team_readiness: float
    business_alignment: float
    
    business_summary: Optional[str]
    readiness_interpretation: Optional[str]
    client_summary: Optional[str]
    reviewer_notes: Optional[str]
    approval_status: Optional[str]
    
    created_at: datetime
    updated_at: datetime
    
    bottlenecks: List[BottleneckResponse] = []
    use_cases: List[UseCaseResponse] = []
    risks: List[RiskResponse] = []
    roadmap_items: List[RoadmapResponse] = []
    extracted_signals: List[SignalResponse] = []
    client: Optional[ClientResponse] = None

    class Config:
        from_attributes = True
