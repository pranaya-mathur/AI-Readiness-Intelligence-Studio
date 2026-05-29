from typing import List, Dict, Any
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
    
    # Document Signals
    extracted_text: str = "" # Consolidated text corpus from uploaded SOPs/files
    extracted_signals: List[Dict[str, Any]] = Field(default_factory=list) # Dicts with source_file, signal_type, description, confidence
    
    # Analysis & Insights
    business_summary: str = ""
    bottlenecks: List[Dict[str, Any]] = Field(default_factory=list) # Dicts with process_name, department, bottleneck_description, ai_potential
    use_cases: List[Dict[str, Any]] = Field(default_factory=list) # Dicts with use_case_name, department, description, value, complexity, risk, priority, evidence, confidence
    
    # Scores
    data_readiness: float = 0.0
    process_readiness: float = 0.0
    integration_readiness: float = 0.0
    governance_readiness: float = 0.0
    security_readiness: float = 0.0
    team_readiness: float = 0.0
    business_alignment: float = 0.0
    overall_score: float = 0.0
    automation_potential: float = 0.0
    readiness_interpretation: str = ""
    
    # Governance & Risks
    risks: List[Dict[str, Any]] = Field(default_factory=list) # Dicts with risk_name, severity, recommendation, is_control_met
    
    # Pilot & Strategy
    recommended_pilot: Dict[str, Any] = Field(default_factory=dict) # keys: name, why, expected_impact, confidence
    
    # Roadmap & Outputs
    roadmap_items: List[Dict[str, Any]] = Field(default_factory=list) # Dicts with phase, action_item, expected_impact, confidence
    proposal_summary: Dict[str, Any] = Field(default_factory=dict)
    
    # Orchestration logs / progress trackers
    logs: List[str] = Field(default_factory=list)
    current_node: str = "init"
