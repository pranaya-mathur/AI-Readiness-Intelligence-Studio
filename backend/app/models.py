import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Integer, default=1)  # 1 = active, 0 = inactive
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    organizations = relationship(
        "Organization", back_populates="owner", cascade="all, delete-orphan"
    )
    assessments = relationship("Assessment", back_populates="user")


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="organizations")
    clients = relationship(
        "Client", back_populates="organization", cascade="all, delete-orphan"
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
    company_name = Column(String, index=True, nullable=False)
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

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    # Relationships
    user = relationship("User", back_populates="assessments")
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
    confidence = Column(Float, default=90.0)

    assessment = relationship("Assessment", back_populates="extracted_signals")
