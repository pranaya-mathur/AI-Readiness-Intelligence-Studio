import datetime

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Integer, default=1)  # 1 = active, 0 = inactive
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    full_name = Column(String, nullable=True)
    organizations = relationship(
        "Organization", back_populates="owner", cascade="all, delete-orphan"
    )
    assessments = relationship(
        "Assessment",
        back_populates="user",
        foreign_keys="[Assessment.user_id]",
    )
    memberships = relationship(
        "OrganizationMembership",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="[OrganizationMembership.user_id]",
    )


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    # Phase 3: enterprise | consulting_agency
    workspace_type = Column(String, nullable=False, default="consulting_agency")
    brand_display_name = Column(String, nullable=True)
    brand_logo_url = Column(String, nullable=True)
    brand_primary_color = Column(String, nullable=True)
    brand_secondary_color = Column(String, nullable=True)
    brand_contact_email = Column(String, nullable=True)
    brand_contact_phone = Column(String, nullable=True)
    brand_footer_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    owner = relationship("User", back_populates="organizations")
    clients = relationship(
        "Client", back_populates="organization", cascade="all, delete-orphan"
    )
    memberships = relationship(
        "OrganizationMembership",
        back_populates="organization",
        cascade="all, delete-orphan",
    )


class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role = Column(String, nullable=False, default="consultant_analyst")
    # Client viewers must be scoped to explicit client engagement IDs.
    # Null/empty for internal roles means organization-wide access.
    authorized_client_ids = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    organization = relationship("Organization", back_populates="memberships")
    user = relationship(
        "User",
        back_populates="memberships",
        foreign_keys=[user_id],
    )


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
    name = Column(String, nullable=False, index=True)
    industry = Column(String, nullable=True)
    company_size = Column(String, nullable=True)
    cloud_preference = Column(String, nullable=True)
    compliance_requirements = Column(JSON, nullable=True)
    # Phase 3 engagement fields
    business_unit = Column(String, nullable=True)
    engagement_status = Column(String, nullable=True, default="draft")
    assigned_consultant_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )
    consultant_notes = Column(Text, nullable=True)
    proposal_package = Column(JSON, nullable=True)
    sow_package = Column(JSON, nullable=True)
    fee_estimate = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    organization = relationship("Organization", back_populates="clients")
    assessments = relationship("Assessment", back_populates="client")


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=True, index=True
    )
    company_name = Column(String, index=True, nullable=False)
    business_unit = Column(String, nullable=True)
    workflow_status = Column(String, nullable=True, default="draft")
    locked_for_delivery = Column(Integer, default=0)
    workflow_approved_at = Column(DateTime, nullable=True)
    workflow_approved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # Proposal/SOW bound to this assessment (not shared across sibling engagements).
    proposal_package = Column(JSON, nullable=True)
    sow_package = Column(JSON, nullable=True)
    fee_estimate = Column(JSON, nullable=True)
    proposal_locked = Column(Integer, default=0)
    proposal_approved_at = Column(DateTime, nullable=True)
    industry = Column(String, nullable=True)
    company_size = Column(String, nullable=True)
    departments = Column(JSON, nullable=True)  # List of departments
    current_tools = Column(JSON, nullable=True)  # List of tools
    cloud_preference = Column(String, nullable=True)
    compliance_requirements = Column(JSON, nullable=True)  # List of requirements
    main_business_goals = Column(Text, nullable=True)

    # Selected cards
    pain_points = Column(JSON, nullable=True)  # List of cards
    ai_goals = Column(JSON, nullable=True)  # List of cards

    # Scoring Breakdown & Metadata
    overall_score = Column(Float, default=0.0)
    automation_potential = Column(Float, default=0.0)  # percentage (e.g. 28%)
    confidence_score = Column(
        Float, default=0.0
    )  # confidence on recommendation (e.g. 85%)
    status = Column(
        String, default="intake"
    )  # intake, uploading, processing, completed
    risk_level = Column(String, default="Low")  # Low, Medium, High
    recommended_first_pilot = Column(String, nullable=True)
    why_recommended_pilot = Column(Text, nullable=True)
    expected_pilot_impact = Column(Text, nullable=True)

    # Detailed Score cards (Data, Process, Integration, Governance, Security, Team, Business Alignment)
    data_readiness = Column(Float, default=0.0)
    data_justification = Column(Text, nullable=True)
    process_readiness = Column(Float, default=0.0)
    process_justification = Column(Text, nullable=True)
    integration_readiness = Column(Float, default=0.0)
    integration_justification = Column(Text, nullable=True)
    governance_readiness = Column(Float, default=0.0)
    governance_justification = Column(Text, nullable=True)
    security_readiness = Column(Float, default=0.0)
    security_justification = Column(Text, nullable=True)
    team_readiness = Column(Float, default=0.0)
    team_justification = Column(Text, nullable=True)
    business_alignment = Column(Float, default=0.0)
    alignment_justification = Column(Text, nullable=True)

    # Interpretation paragraphs
    business_summary = Column(Text, nullable=True)
    readiness_interpretation = Column(Text, nullable=True)
    client_summary = Column(Text, nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    approval_status = Column(String, default="draft")  # draft, reviewed, approved

    # Phase 1: scoring / model transparency (additive)
    scoring_rubric_version = Column(String, nullable=True)
    scoring_method = Column(String, nullable=True)
    dimension_score_details = Column(JSON, nullable=True)
    automation_potential_basis = Column(String, nullable=True)
    analysis_mode = Column(String, nullable=True)  # real | demo
    model_provider = Column(String, nullable=True)
    model_name = Column(String, nullable=True)
    model_run_status = Column(String, nullable=True)
    model_error = Column(Text, nullable=True)
    evidence_package = Column(JSON, nullable=True)
    insufficient_evidence = Column(Integer, default=0)  # 0/1

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    # Phase 2: investment decision intelligence (additive)
    prioritization_rubric_version = Column(String, nullable=True)
    financial_model_version = Column(String, nullable=True)
    investment_package = Column(JSON, nullable=True)
    investment_decision_status = Column(
        String, nullable=True
    )  # invest | validate_first | defer | not_recommended | pending_review
    investment_decision_explanation = Column(Text, nullable=True)
    investment_decision_reviewer_id = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    investment_decision_at = Column(DateTime, nullable=True)
    recommended_opportunity_id = Column(Integer, nullable=True)
    pilot_plan = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User", back_populates="assessments", foreign_keys=[user_id])
    client = relationship("Client", back_populates="assessments")
    bottlenecks = relationship(
        "ProcessBottleneck", back_populates="assessment", cascade="all, delete-orphan"
    )
    use_cases = relationship(
        "AIUseCase", back_populates="assessment", cascade="all, delete-orphan"
    )
    risks = relationship(
        "RiskRegister", back_populates="assessment", cascade="all, delete-orphan"
    )
    roadmap_items = relationship(
        "RoadmapItem", back_populates="assessment", cascade="all, delete-orphan"
    )
    extracted_signals = relationship(
        "DocumentSignal", back_populates="assessment", cascade="all, delete-orphan"
    )
    opportunity_evaluations = relationship(
        "OpportunityEvaluation",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )
    investment_review_events = relationship(
        "InvestmentReviewEvent",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )


class ProcessBottleneck(Base):
    __tablename__ = "process_bottlenecks"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(
        Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False
    )
    department = Column(String, nullable=False)
    process_name = Column(String, nullable=False)
    bottleneck_description = Column(Text, nullable=False)
    ai_potential = Column(String, default="Medium")  # High, Medium, Low
    evidence_refs = Column(JSON, nullable=True)  # list[str] evidence_ids

    assessment = relationship("Assessment", back_populates="bottlenecks")


class AIUseCase(Base):
    __tablename__ = "ai_use_cases"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(
        Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False
    )
    department = Column(String, nullable=False)
    use_case_name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    value = Column(String, default="High")  # High, Medium, Low
    complexity = Column(String, default="Medium")  # High, Medium, Low
    risk = Column(String, default="Low")  # High, Medium, Low
    priority = Column(String, default="P1")  # P1, P2, P3
    evidence = Column(
        Text, nullable=True
    )  # Recommended because uploaded documents show...
    confidence = Column(Float, default=85.0)  # Confidence level in recommendation
    evidence_refs = Column(JSON, nullable=True)  # list[str] evidence_ids

    assessment = relationship("Assessment", back_populates="use_cases")


class RiskRegister(Base):
    __tablename__ = "risk_registers"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(
        Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False
    )
    risk_name = Column(String, nullable=False)
    severity = Column(String, default="Medium")  # High, Medium, Low
    recommendation = Column(Text, nullable=False)
    is_control_met = Column(Integer, default=0)  # 0 = No, 1 = Yes
    evidence_refs = Column(JSON, nullable=True)  # list[str] evidence_ids

    assessment = relationship("Assessment", back_populates="risks")


class RoadmapItem(Base):
    __tablename__ = "roadmap_items"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(
        Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False
    )
    phase = Column(String, nullable=False)  # "30-Day", "60-Day", "90-Day"
    action_item = Column(String, nullable=False)
    expected_impact = Column(Text, nullable=False)
    confidence = Column(Float, default=80.0)

    assessment = relationship("Assessment", back_populates="roadmap_items")


class DocumentSignal(Base):
    __tablename__ = "document_signals"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(
        Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False
    )
    source_file = Column(String, nullable=False)
    signal_type = Column(
        String, nullable=False
    )  # SOP, Process, Tech Stack, Governance Gap
    description = Column(Text, nullable=False)
    confidence = Column(Float, default=0.0)  # uncalibrated; prefer evidence_tier
    document_id = Column(String, nullable=True)
    excerpt = Column(Text, nullable=True)
    page_or_section = Column(String, nullable=True)
    evidence_tier = Column(String, nullable=True)
    evidence_id = Column(String, nullable=True)

    assessment = relationship("Assessment", back_populates="extracted_signals")


class OpportunityEvaluation(Base):
    """Phase 2 evaluated opportunity linked to a discovered AI use case."""

    __tablename__ = "opportunity_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(
        Integer,
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    use_case_id = Column(
        Integer,
        ForeignKey("ai_use_cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    department = Column(String, nullable=True)

    criterion_scores = Column(JSON, nullable=True)
    criterion_weights = Column(JSON, nullable=True)
    original_criterion_scores = Column(JSON, nullable=True)
    reviewed_criterion_scores = Column(JSON, nullable=True)
    weighted_priority_score = Column(Float, nullable=True)
    original_priority_score = Column(Float, nullable=True)
    ranking = Column(Integer, nullable=True)
    ranking_explanation = Column(Text, nullable=True)
    evidence_refs = Column(JSON, nullable=True)
    missing_information = Column(JSON, nullable=True)
    confidence_class = Column(String, nullable=True)
    recommendation_status = Column(String, nullable=True)
    hard_blockers = Column(JSON, nullable=True)
    is_blocked = Column(Integer, default=0)

    feasibility = Column(JSON, nullable=True)
    financial_inputs = Column(JSON, nullable=True)
    original_financial_inputs = Column(JSON, nullable=True)
    financial_evaluation = Column(JSON, nullable=True)
    pilot_selected = Column(Integer, default=0)

    prioritization_rubric_version = Column(String, nullable=True)
    financial_model_version = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    assessment = relationship("Assessment", back_populates="opportunity_evaluations")


class InvestmentReviewEvent(Base):
    """Audit trail for human overrides of investment intelligence values."""

    __tablename__ = "investment_review_events"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(
        Integer,
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    opportunity_evaluation_id = Column(Integer, nullable=True, index=True)
    reviewer_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    event_type = Column(String, nullable=False)
    field_name = Column(String, nullable=True)
    previous_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    reason = Column(Text, nullable=True)
    prioritization_rubric_version = Column(String, nullable=True)
    financial_model_version = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    assessment = relationship("Assessment", back_populates="investment_review_events")
