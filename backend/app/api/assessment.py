import io
import logging
import os

import fitz  # PyMuPDF for quick PDF parses
from docx import Document as DocxDocument
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.agents.graph import AssessmentOrchestrator
from app.api.auth import get_current_user
from app.api.clients import get_client_for_user, get_or_create_default_organization
from app.core.config import settings
from app.core.database import get_db
from app.core.sanitizer import sanitize_text
from app.models import (
    AIUseCase,
    Assessment,
    Client,
    DocumentSignal,
    ProcessBottleneck,
    RiskRegister,
    RoadmapItem,
    User,
)
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentResponse,
    AssessmentUpdate,
)
from app.services.document_generators import DocumentGenerators
from app.services.evidence_links import (
    enrich_finding_with_validated_refs,
    index_assessment_evidence,
)
from app.services.scoring import ScoringEngine

logger = logging.getLogger("AssessmentAPI")
router = APIRouter()

orchestrator = AssessmentOrchestrator()
VALID_APPROVAL_STATUSES = {"draft", "reviewed", "approved"}


def _assessment_is_client_exportable(ass: Assessment) -> tuple[bool, str]:
    """Real client exports require a completed, non-demo, non-simulated analysis."""
    status = (ass.status or "").lower()
    if status in {"incomplete", "failed", "processing", "intake", "uploading"}:
        return (
            False,
            f"Assessment status '{status}' is not exportable as a verified client report",
        )
    analysis_mode = (getattr(ass, "analysis_mode", None) or "").lower()
    model_status = (getattr(ass, "model_run_status", None) or "").lower()
    if analysis_mode == "demo" or model_status == "demo_simulated":
        return (
            False,
            "Demo/simulated analysis cannot be exported as a verified client assessment",
        )
    if getattr(ass, "insufficient_evidence", 0):
        # Still allow export after human approval only if not incomplete/demo;
        # insufficient evidence alone is a warning, not a hard block once reviewed.
        pass
    return True, ""


def _is_internal_demo_export(ass: Assessment, mode: str | None) -> bool:
    """Allow export bypass only for genuine demo/simulated assessments in demo envs.

    Real assessments always require successful completion + human approval for
    PDF/DOCX/PPTX exports, regardless of ``mode=demo`` query parameter.
    """
    if (mode or "").lower() != "demo":
        return False
    # Authorized demo environments only — never unlock production client exports.
    if not (settings.ENABLE_DEMO_WORKSPACE or settings.DEMO_MODE):
        return False
    analysis_mode = (getattr(ass, "analysis_mode", None) or "").lower()
    model_status = (getattr(ass, "model_run_status", None) or "").lower()
    return analysis_mode == "demo" or model_status in {
        "demo_simulated",
        "simulated",
    }


def normalize_department(use_case_name: str, description: str) -> str:
    n = (use_case_name or "").lower()
    d = (description or "").lower()

    # 1. Sales & Pre-sales
    if any(
        x in n or x in d
        for x in [
            "proposal",
            "rfp",
            "pre-sales",
            "sales",
            "pricing",
            "client email",
            "bid",
        ]
    ):
        return "Sales & Pre-sales"
    # 2. Customer Support
    if any(
        x in n or x in d
        for x in ["support", "ticket", "triage", "incident", "response assistant"]
    ):
        return "Customer Support"
    # 3. Operations
    if any(
        x in n or x in d
        for x in ["billing", "invoice", "reconciliation", "spreadsheet", "excel"]
    ):
        return "Operations"
    # 4. Compliance & Governance
    if any(
        x in n or x in d
        for x in ["governance", "compliance", "audit", "contract", "policy"]
    ):
        return "Compliance & Governance"
    return "Operations"


# Helper to load DB assessment into dict format for generators or orchestrators
def _db_assessment_to_dict(ass: Assessment) -> dict:
    return {
        "id": ass.id,
        "company_name": ass.company_name,
        "industry": ass.industry,
        "company_size": ass.company_size,
        "departments": ass.departments,
        "current_tools": ass.current_tools,
        "cloud_preference": ass.cloud_preference,
        "compliance_requirements": ass.compliance_requirements,
        "main_business_goals": ass.main_business_goals,
        "pain_points": ass.pain_points,
        "ai_goals": ass.ai_goals,
        "overall_score": ass.overall_score,
        "automation_potential": ass.automation_potential,
        "confidence_score": ass.confidence_score,
        "status": ass.status,
        "risk_level": ass.risk_level,
        "recommended_first_pilot": ass.recommended_first_pilot,
        "why_recommended_pilot": ass.why_recommended_pilot,
        "expected_pilot_impact": ass.expected_pilot_impact,
        "data_readiness": ass.data_readiness,
        "data_justification": ass.data_justification,
        "process_readiness": ass.process_readiness,
        "process_justification": ass.process_justification,
        "integration_readiness": ass.integration_readiness,
        "integration_justification": ass.integration_justification,
        "governance_readiness": ass.governance_readiness,
        "governance_justification": ass.governance_justification,
        "security_readiness": ass.security_readiness,
        "security_justification": ass.security_justification,
        "team_readiness": ass.team_readiness,
        "team_justification": ass.team_justification,
        "business_alignment": ass.business_alignment,
        "alignment_justification": ass.alignment_justification,
        "business_summary": ass.business_summary,
        "client_summary": ass.client_summary,
        "reviewer_notes": ass.reviewer_notes,
        "approval_status": ass.approval_status,
        "readiness_interpretation": ass.readiness_interpretation,
        "bottlenecks": [
            {
                "department": b.department,
                "process_name": b.process_name,
                "bottleneck_description": b.bottleneck_description,
                "ai_potential": b.ai_potential,
                "evidence_refs": getattr(b, "evidence_refs", None) or [],
            }
            for b in ass.bottlenecks
        ],
        "use_cases": [
            {
                "use_case_name": u.use_case_name,
                "department": normalize_department(u.use_case_name, u.description),
                "description": u.description,
                "value": u.value,
                "complexity": u.complexity,
                "risk": u.risk,
                "priority": u.priority,
                "evidence": u.evidence,
                "confidence": u.confidence,
                "evidence_refs": getattr(u, "evidence_refs", None) or [],
            }
            for u in ass.use_cases
        ],
        "risks": [
            {
                "risk_name": r.risk_name,
                "severity": r.severity,
                "recommendation": r.recommendation,
                "is_control_met": r.is_control_met,
                "evidence_refs": getattr(r, "evidence_refs", None) or [],
            }
            for r in ass.risks
        ],
        "roadmap_items": [
            {
                "phase": rm.phase,
                "action_item": rm.action_item,
                "expected_impact": rm.expected_impact,
                "confidence": rm.confidence,
            }
            for rm in ass.roadmap_items
        ],
        "extracted_signals": [
            {
                "source_file": s.source_file,
                "signal_type": s.signal_type,
                "description": s.description,
                "confidence": s.confidence,
                "document_id": getattr(s, "document_id", None),
                "excerpt": getattr(s, "excerpt", None),
                "page_or_section": getattr(s, "page_or_section", None),
                "evidence_tier": getattr(s, "evidence_tier", None),
                "evidence_id": getattr(s, "evidence_id", None),
            }
            for s in ass.extracted_signals
        ],
        "scoring_rubric_version": getattr(ass, "scoring_rubric_version", None),
        "scoring_method": getattr(ass, "scoring_method", None),
        "dimension_score_details": getattr(ass, "dimension_score_details", None),
        "automation_potential_basis": getattr(ass, "automation_potential_basis", None),
        "prioritization_rubric_version": getattr(
            ass, "prioritization_rubric_version", None
        ),
        "financial_model_version": getattr(ass, "financial_model_version", None),
        "investment_decision_status": getattr(ass, "investment_decision_status", None),
        "investment_decision_explanation": getattr(
            ass, "investment_decision_explanation", None
        ),
        "recommended_opportunity_id": getattr(ass, "recommended_opportunity_id", None),
        "pilot_plan": getattr(ass, "pilot_plan", None),
        "investment_package": getattr(ass, "investment_package", None),
        "analysis_mode": getattr(ass, "analysis_mode", None),
        "model_provider": getattr(ass, "model_provider", None),
        "model_name": getattr(ass, "model_name", None),
        "model_run_status": getattr(ass, "model_run_status", None),
        "model_error": getattr(ass, "model_error", None),
        "evidence_package": getattr(ass, "evidence_package", None),
        "insufficient_evidence": getattr(ass, "insufficient_evidence", 0),
    }


@router.post("/", response_model=AssessmentResponse)
def create_assessment(
    payload: AssessmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Creates a blank assessment session based on Intake details"""
    logger.info(f"Creating intake session for: {payload.company_name}")
    organization = get_or_create_default_organization(db, current_user)
    client = None

    if payload.client_id is not None:
        client = get_client_for_user(db, current_user, payload.client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
    else:
        client = (
            db.query(Client)
            .filter(
                Client.organization_id == organization.id,
                Client.name == payload.company_name,
            )
            .first()
        )
        if not client:
            client = Client(
                organization_id=organization.id,
                name=payload.company_name,
                industry=payload.industry,
                company_size=payload.company_size,
                cloud_preference=payload.cloud_preference,
                compliance_requirements=payload.compliance_requirements,
            )
            db.add(client)
            db.flush()

    ass = Assessment(
        user_id=current_user.id,
        client_id=client.id,
        company_name=client.name,
        industry=payload.industry or client.industry,
        company_size=payload.company_size or client.company_size,
        departments=payload.departments,
        current_tools=payload.current_tools,
        cloud_preference=payload.cloud_preference or client.cloud_preference,
        compliance_requirements=payload.compliance_requirements
        or (client.compliance_requirements if client else []),
        main_business_goals=payload.main_business_goals,
        pain_points=payload.pain_points,
        ai_goals=payload.ai_goals,
        status="intake",
    )
    db.add(ass)
    db.commit()
    db.refresh(ass)
    return ass


@router.get("/", response_model=list[AssessmentResponse])
def list_assessments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Assessment)
        .filter(Assessment.user_id == current_user.id)
        .order_by(Assessment.updated_at.desc())
        .all()
    )


@router.delete("/{id}", status_code=204)
def delete_assessment(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ass = (
        db.query(Assessment)
        .filter(Assessment.id == id, Assessment.user_id == current_user.id)
        .first()
    )
    if not ass:
        raise HTTPException(status_code=404, detail="Assessment not found")

    db.delete(ass)
    db.commit()


@router.get("/{id}", response_model=AssessmentResponse)
def get_assessment(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves full assessment with all related details loaded"""
    ass = (
        db.query(Assessment)
        .filter(Assessment.id == id, Assessment.user_id == current_user.id)
        .first()
    )
    if not ass:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return ass


def _validate_upload_file(upload: UploadFile, content: bytes) -> None:
    filename = upload.filename or "upload.bin"
    _, ext = os.path.splitext(filename.lower())
    if ext not in settings.allowed_upload_extensions:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{ext}'. Allowed: "
                f"{', '.join(settings.allowed_upload_extensions)}"
            ),
        )
    if len(content) > settings.MAX_UPLOAD_FILE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"File '{filename}' exceeds max size of "
                f"{settings.MAX_UPLOAD_FILE_BYTES} bytes"
            ),
        )


def _parse_upload_bytes(filename: str, content: bytes) -> tuple[str, list, str | None]:
    """Returns (text, pages, parse_error)."""
    pages: list = []
    try:
        lower = filename.lower()
        if lower.endswith(".pdf"):
            doc = fitz.open(stream=content, filetype="pdf")
            chunks: list[str] = []
            for idx, page in enumerate(doc, start=1):
                page_text = page.get_text() or ""
                pages.append({"page": idx, "text": page_text})
                chunks.append(page_text)
            return "\n".join(chunks), pages, None
        if lower.endswith(".docx"):
            doc = DocxDocument(io.BytesIO(content))
            paragraph_text = [
                paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()
            ]
            table_text = []
            for table in doc.tables:
                for row in table.rows:
                    cells = [
                        cell.text.strip() for cell in row.cells if cell.text.strip()
                    ]
                    if cells:
                        table_text.append(" | ".join(cells))
            text = "\n".join(paragraph_text + table_text)
            return text, [{"page": 1, "text": text}], None
        text = content.decode("utf-8", errors="ignore")
        return text, [{"page": 1, "text": text}], None
    except Exception as exc:
        return "", [], str(exc)


@router.post("/{id}/upload", response_model=AssessmentResponse)
def upload_documents(
    id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Parses uploaded files, populates evidence corpus, and executes the LangGraph analysis"""
    ass = (
        db.query(Assessment)
        .filter(Assessment.id == id, Assessment.user_id == current_user.id)
        .first()
    )
    if not ass:
        raise HTTPException(status_code=404, detail="Assessment not found")

    if len(files) > settings.MAX_UPLOAD_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files. Max allowed is {settings.MAX_UPLOAD_FILES}.",
        )

    ass.status = "processing"
    db.commit()

    documents = []
    extracted_corpus = []

    for f in files:
        content = f.file.read()
        filename = f.filename or "upload.bin"
        try:
            _validate_upload_file(f, content)
        except HTTPException:
            ass.status = "failed"
            db.commit()
            raise

        file_text, pages, parse_error = _parse_upload_bytes(filename, content)
        documents.append(
            {
                "filename": filename,
                "text": file_text,
                "pages": pages,
                "parse_error": parse_error,
            }
        )
        if parse_error:
            logger.error("Error parsing file %s: %s", filename, parse_error)
        else:
            extracted_corpus.append(f"--- File: {filename} ---\n{file_text}")

    consolidated_text = "\n\n".join(extracted_corpus)

    initial_graph_state = {
        "assessment_id": ass.id,
        "company_name": ass.company_name,
        "industry": ass.industry or "Technology Services",
        "company_size": ass.company_size or "10-100 employees",
        "departments": ass.departments or [],
        "current_tools": ass.current_tools or [],
        "cloud_preference": ass.cloud_preference or "Cloud-agnostic",
        "compliance_requirements": ass.compliance_requirements or [],
        "main_business_goals": ass.main_business_goals or "",
        "pain_points": ass.pain_points or [],
        "ai_goals": ass.ai_goals or [],
        "extracted_text": consolidated_text,
        "documents": documents,
        "analysis_mode": "demo" if settings.DEMO_MODE else "real",
    }

    try:
        final_state = orchestrator.run_assessment(
            initial_graph_state, thread_id=f"thread_{ass.id}"
        )

        incomplete = bool(final_state.get("analysis_incomplete"))
        ass.business_summary = sanitize_text(
            final_state.get("business_summary"),
            "Insufficient verified evidence for a complete business summary.",
        )
        ass.client_summary = sanitize_text(
            final_state.get("business_summary"),
            "Insufficient verified evidence for a complete client summary.",
        )
        ass.approval_status = "draft"
        ass.overall_score = float(final_state.get("overall_score", 0.0) or 0.0)
        ass.automation_potential = float(
            final_state.get("automation_potential", 0.0) or 0.0
        )
        # Confidence is uncalibrated; do not present LLM percentages as certainty.
        ass.confidence_score = 0.0
        ass.readiness_interpretation = sanitize_text(
            final_state.get("readiness_interpretation"),
            "Insufficient verified evidence for a firm readiness interpretation.",
        )

        ass.data_readiness = float(final_state.get("data_readiness", 0.0) or 0.0)
        ass.data_justification = sanitize_text(
            final_state.get("data_justification"),
            "Missing verified data evidence.",
        )
        ass.process_readiness = float(final_state.get("process_readiness", 0.0) or 0.0)
        ass.process_justification = sanitize_text(
            final_state.get("process_justification"),
            "Missing verified process evidence.",
        )
        ass.integration_readiness = float(
            final_state.get("integration_readiness", 0.0) or 0.0
        )
        ass.integration_justification = sanitize_text(
            final_state.get("integration_justification"),
            "Missing verified integration evidence.",
        )
        ass.governance_readiness = float(
            final_state.get("governance_readiness", 0.0) or 0.0
        )
        ass.governance_justification = sanitize_text(
            final_state.get("governance_justification"),
            "Missing verified governance evidence.",
        )
        ass.security_readiness = float(
            final_state.get("security_readiness", 0.0) or 0.0
        )
        ass.security_justification = sanitize_text(
            final_state.get("security_justification"),
            "Missing verified security evidence.",
        )
        ass.team_readiness = float(final_state.get("team_readiness", 0.0) or 0.0)
        ass.team_justification = sanitize_text(
            final_state.get("team_justification"),
            "Missing verified team readiness evidence.",
        )
        ass.business_alignment = float(
            final_state.get("business_alignment", 0.0) or 0.0
        )
        ass.alignment_justification = sanitize_text(
            final_state.get("alignment_justification"),
            "Missing verified business alignment evidence.",
        )

        # Always recompute overall deterministically from persisted dimension scores.
        ass.overall_score = ScoringEngine.recompute_overall_from_assessment_fields(
            {
                "data_readiness": ass.data_readiness,
                "process_readiness": ass.process_readiness,
                "integration_readiness": ass.integration_readiness,
                "governance_readiness": ass.governance_readiness,
                "security_readiness": ass.security_readiness,
                "team_readiness": ass.team_readiness,
                "business_alignment": ass.business_alignment,
            }
        )

        ass.scoring_rubric_version = final_state.get("scoring_rubric_version")
        ass.scoring_method = final_state.get("scoring_method")
        ass.dimension_score_details = final_state.get("dimension_score_details")
        ass.automation_potential_basis = final_state.get("automation_potential_basis")
        ass.analysis_mode = final_state.get("analysis_mode") or (
            "demo" if settings.DEMO_MODE else "real"
        )
        ass.model_provider = final_state.get("model_provider")
        ass.model_name = final_state.get("model_name")
        ass.model_run_status = final_state.get("model_run_status")
        ass.model_error = final_state.get("model_error") or final_state.get(
            "incomplete_reason"
        )
        ass.evidence_package = final_state.get("evidence_package")
        ass.insufficient_evidence = 1 if final_state.get("insufficient_evidence") else 0

        ass.risk_level = (
            "High"
            if any(r.get("severity") == "High" for r in final_state.get("risks", []))
            else "Medium"
        )

        pilot = final_state.get("recommended_pilot", {}) or {}
        ass.recommended_first_pilot = sanitize_text(
            pilot.get("name"),
            "Evidence Completion Sprint"
            if final_state.get("insufficient_evidence")
            else "Pilot recommendation unavailable",
        )
        ass.why_recommended_pilot = sanitize_text(
            pilot.get("why"),
            "Insufficient verified evidence for a firm pilot recommendation.",
        )
        ass.expected_pilot_impact = sanitize_text(
            pilot.get("expected_impact"),
            "Impact is an estimate only and is not supported by measured data.",
        )

        db.query(ProcessBottleneck).filter(
            ProcessBottleneck.assessment_id == ass.id
        ).delete()
        evidence_index = index_assessment_evidence(
            (final_state.get("evidence_package") or {}).get("evidence_items") or []
        )
        for b in final_state.get("bottlenecks", []):
            validated = enrich_finding_with_validated_refs(b, evidence_index)
            db.add(
                ProcessBottleneck(
                    assessment_id=ass.id,
                    department=validated.get("department", "Unknown"),
                    process_name=sanitize_text(
                        validated.get("process_name"), "Insufficient Evidence"
                    ),
                    bottleneck_description=sanitize_text(
                        validated.get("bottleneck_description"),
                        "Insufficient verified evidence to describe this bottleneck.",
                    ),
                    ai_potential=validated.get("ai_potential", "Unknown"),
                    evidence_refs=validated.get("evidence_refs") or [],
                )
            )

        db.query(AIUseCase).filter(AIUseCase.assessment_id == ass.id).delete()
        for u in final_state.get("use_cases", []):
            validated = enrich_finding_with_validated_refs(u, evidence_index)
            uc_name = sanitize_text(
                validated.get("use_case_name"),
                "Insufficient Evidence — Discovery Deferred",
            )
            uc_desc = sanitize_text(
                validated.get("description"),
                "Use-case discovery incomplete due to missing verified evidence.",
            )
            db.add(
                AIUseCase(
                    assessment_id=ass.id,
                    department=normalize_department(uc_name, uc_desc),
                    use_case_name=uc_name,
                    description=uc_desc,
                    value=validated.get("value", "Unknown"),
                    complexity=validated.get("complexity", "Unknown"),
                    risk=validated.get("risk", "Unknown"),
                    priority=validated.get("priority", "P3"),
                    evidence=sanitize_text(
                        validated.get("evidence"),
                        "Insufficient verified evidence.",
                    ),
                    confidence=0.0,
                    evidence_refs=validated.get("evidence_refs") or [],
                )
            )

        db.query(RiskRegister).filter(RiskRegister.assessment_id == ass.id).delete()
        for r in final_state.get("risks", []):
            validated = enrich_finding_with_validated_refs(r, evidence_index)
            # Keyword/document cues never prove a control is met.
            control_met = 0
            if validated.get("evidence_tier") == "verified" and validated.get(
                "evidence_refs"
            ):
                control_met = int(validated.get("is_control_met", 0) or 0)
            db.add(
                RiskRegister(
                    assessment_id=ass.id,
                    risk_name=sanitize_text(
                        validated.get("risk_name"),
                        "Insufficient Evidence for Risk Closure",
                    ),
                    severity=validated.get("severity", "High"),
                    recommendation=sanitize_text(
                        validated.get("recommendation"),
                        "Collect verified governance/security evidence before external model use.",
                    ),
                    is_control_met=control_met,
                    evidence_refs=validated.get("evidence_refs") or [],
                )
            )

        db.query(RoadmapItem).filter(RoadmapItem.assessment_id == ass.id).delete()
        for item in final_state.get("roadmap_items", []):
            db.add(
                RoadmapItem(
                    assessment_id=ass.id,
                    phase=item.get("phase", "30-Day"),
                    action_item=sanitize_text(
                        item.get("action_item"),
                        "Collect missing evidence before pilot build.",
                    ),
                    expected_impact=sanitize_text(
                        item.get("expected_impact"),
                        "Estimate only — not supported by measured data.",
                    ),
                    confidence=0.0,
                )
            )

        # Replace prior upload/analysis signals with provenance-rich evidence rows.
        db.query(DocumentSignal).filter(DocumentSignal.assessment_id == ass.id).delete()
        for signal in final_state.get("extracted_signals", []):
            db.add(
                DocumentSignal(
                    assessment_id=ass.id,
                    source_file=signal.get("source_file") or "unknown",
                    signal_type=signal.get("signal_type") or "Evidence",
                    description=sanitize_text(
                        signal.get("description"), "Evidence item"
                    ),
                    confidence=0.0,
                    document_id=signal.get("document_id"),
                    excerpt=signal.get("excerpt"),
                    page_or_section=signal.get("page_or_section"),
                    evidence_tier=signal.get("evidence_tier"),
                    evidence_id=signal.get("evidence_id"),
                )
            )

        db.add(
            DocumentSignal(
                assessment_id=ass.id,
                source_file="LangGraphOrchestrator",
                signal_type="Execution Incomplete"
                if incomplete
                else "Execution Complete",
                description=(
                    final_state.get("incomplete_reason")
                    or (
                        f"Pipeline finished. provider={ass.model_provider} "
                        f"model={ass.model_name} status={ass.model_run_status} "
                        f"mode={ass.analysis_mode}"
                    )
                ),
                confidence=0.0,
                evidence_tier="missing" if incomplete else "verified",
            )
        )

        ass.status = "incomplete" if incomplete else "completed"
        db.flush()
        # Phase 2: deterministic investment intelligence over discovered use cases.
        try:
            from app.services.investment_persistence import (
                build_and_persist_investment_package,
            )

            build_and_persist_investment_package(db, ass)
        except Exception as invest_exc:
            logger.error(f"Investment intelligence build failed: {invest_exc}")
            # Do not fail Phase 1 analysis if Phase 2 package construction errors;
            # surface via model_error note while keeping assessment results.
            ass.model_error = (
                (ass.model_error + " | " if ass.model_error else "")
                + f"investment_intelligence_error: {invest_exc}"
            )

        db.commit()
        db.refresh(ass)

        if incomplete and not settings.DEMO_MODE:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Verified model analysis could not complete: "
                    f"{final_state.get('incomplete_reason') or ass.model_error}"
                ),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LangGraph execution crashed: {e}")
        ass.status = "failed"
        ass.model_run_status = "failed"
        ass.model_error = str(e)
        db.add(
            DocumentSignal(
                assessment_id=ass.id,
                source_file="LangGraphOrchestrator",
                signal_type="Execution Failure",
                description=f"Pipeline crashed with message: {e!s}",
                confidence=0.0,
                evidence_tier="missing",
            )
        )
        db.commit()
        raise HTTPException(status_code=500, detail=f"AI Graph analysis failed: {e!s}")

    return ass


@router.put("/{id}", response_model=AssessmentResponse)
def update_assessment(
    id: int,
    payload: AssessmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Human Review Mode: allows overriding any score or list item manually"""
    ass = (
        db.query(Assessment)
        .filter(Assessment.id == id, Assessment.user_id == current_user.id)
        .first()
    )
    if not ass:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # Standard overrides
    update_data = payload.model_dump(exclude_unset=True)

    # Pop nested items to handle separately
    use_cases = update_data.pop("use_cases", None)
    bottlenecks = update_data.pop("bottlenecks", None)
    risks = update_data.pop("risks", None)
    roadmap_items = update_data.pop("roadmap_items", None)

    for key, value in update_data.items():
        if key == "client_id":
            if value is None:
                ass.client_id = None
                continue
            client = get_client_for_user(db, current_user, value)
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
            ass.client_id = client.id
            ass.company_name = client.name
            continue
        if (
            key == "approval_status"
            and value is not None
            and value not in VALID_APPROVAL_STATUSES
        ):
            raise HTTPException(status_code=400, detail="Invalid approval status")
        if key == "approval_status" and value in {"reviewed", "approved"}:
            exportable, _reason = _assessment_is_client_exportable(ass)
            # Demo/simulated/incomplete cannot be promoted as verified client assessments.
            if (
                not exportable
                and (getattr(ass, "analysis_mode", "") or "").lower() == "demo"
            ):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Demo/simulated assessments cannot be approved as verified "
                        "client deliverables. Use internal demo export mode instead."
                    ),
                )
            if (ass.status or "").lower() in {"incomplete", "failed"}:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Cannot approve an assessment with status '{ass.status}'. "
                        "Re-run analysis successfully first."
                    ),
                )
            if (getattr(ass, "model_run_status", "") or "").lower() == "demo_simulated":
                raise HTTPException(
                    status_code=409,
                    detail="Simulated model output cannot be approved as verified analysis.",
                )
        setattr(ass, key, value)

    # Update Use Cases if provided
    if use_cases is not None:
        db.query(AIUseCase).filter(AIUseCase.assessment_id == id).delete()
        for u in use_cases:
            uc_name = u.get("use_case_name")
            uc_desc = u.get("description")
            db.add(
                AIUseCase(
                    assessment_id=id,
                    department=normalize_department(uc_name, uc_desc),
                    use_case_name=uc_name,
                    description=uc_desc,
                    value=u.get("value"),
                    complexity=u.get("complexity"),
                    risk=u.get("risk"),
                    priority=u.get("priority"),
                    evidence=u.get("evidence"),
                    confidence=u.get("confidence", 85.0),
                )
            )

    # Update Bottlenecks if provided
    if bottlenecks is not None:
        db.query(ProcessBottleneck).filter(
            ProcessBottleneck.assessment_id == id
        ).delete()
        for b in bottlenecks:
            db.add(
                ProcessBottleneck(
                    assessment_id=id,
                    department=b.get("department"),
                    process_name=b.get("process_name"),
                    bottleneck_description=b.get("bottleneck_description"),
                    ai_potential=b.get("ai_potential"),
                )
            )

    # Update Risks if provided
    if risks is not None:
        db.query(RiskRegister).filter(RiskRegister.assessment_id == id).delete()
        for r in risks:
            db.add(
                RiskRegister(
                    assessment_id=id,
                    risk_name=r.get("risk_name"),
                    severity=r.get("severity"),
                    recommendation=r.get("recommendation"),
                    is_control_met=r.get("is_control_met", 0),
                )
            )

    # Update Roadmap if provided
    if roadmap_items is not None:
        db.query(RoadmapItem).filter(RoadmapItem.assessment_id == id).delete()
        for item in roadmap_items:
            db.add(
                RoadmapItem(
                    assessment_id=id,
                    phase=item.get("phase"),
                    action_item=item.get("action_item"),
                    expected_impact=item.get("expected_impact"),
                    confidence=item.get("confidence", 80.0),
                )
            )

    # Deterministic overall from dimension scores (never trust an arbitrary LLM overall).
    dimension_keys = {
        "data_readiness",
        "process_readiness",
        "integration_readiness",
        "governance_readiness",
        "security_readiness",
        "team_readiness",
        "business_alignment",
    }
    if (
        dimension_keys.intersection(update_data.keys())
        or "overall_score" in update_data
    ):
        ass.overall_score = ScoringEngine.recompute_overall_from_assessment_fields(
            {
                "data_readiness": ass.data_readiness or 0.0,
                "process_readiness": ass.process_readiness or 0.0,
                "integration_readiness": ass.integration_readiness or 0.0,
                "governance_readiness": ass.governance_readiness or 0.0,
                "security_readiness": ass.security_readiness or 0.0,
                "team_readiness": ass.team_readiness or 0.0,
                "business_alignment": ass.business_alignment or 0.0,
            }
        )
        ass.scoring_method = "deterministic_rubric_v1_human_reviewed"

    # Re-calculate readiness interpretation dynamically on manual score changes
    if "readiness_interpretation" not in update_data:
        prefix = "With a consultant-reviewed AI readiness score of"
        overall = ass.overall_score
        integration = ass.integration_readiness
        ass.readiness_interpretation = (
            f"{prefix} {int(overall)}/100, the organization appears ready for a controlled pilot rollout, "
            f"while integration ({int(integration)}/100) and governance controls should still be validated "
            f"before production scaling."
        )

    db.commit()
    db.refresh(ass)
    return ass


@router.get("/{id}/export/{doc_format}")
def export_assessment_report(
    id: int,
    doc_format: str,
    mode: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exports compiled custom formatted PDF, DOCX, or PPTX reports"""
    ass = (
        db.query(Assessment)
        .filter(Assessment.id == id, Assessment.user_id == current_user.id)
        .first()
    )
    if not ass:
        raise HTTPException(status_code=404, detail="Assessment not found")
    internal_demo = _is_internal_demo_export(ass, mode)
    if internal_demo:
        # Clearly marked internal demo path — not a verified client deliverable.
        data = _db_assessment_to_dict(ass)
        data["export_mode"] = "demo"
        data["client_summary"] = "[DEMO_SIMULATED / INTERNAL ONLY] " + (
            data.get("client_summary") or data.get("business_summary") or ""
        )
        data["company_name"] = f"[DEMO] {data.get('company_name') or 'Demo Client'}"
    else:
        if ass.approval_status != "approved":
            raise HTTPException(
                status_code=409,
                detail="Assessment must be approved in Human Review Mode before export.",
            )
        exportable, reason = _assessment_is_client_exportable(ass)
        if not exportable:
            raise HTTPException(status_code=409, detail=reason)

        # Serialize DB object to dictionary structure
        data = _db_assessment_to_dict(ass)
        data["export_mode"] = mode

    if doc_format.lower() == "pdf":
        pdf_buffer = DocumentGenerators.generate_pdf_report(data)
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={ass.company_name.replace(' ', '_')}_AI_Readiness_Report.pdf"
            },
        )
    elif doc_format.lower() == "docx":
        docx_buffer = DocumentGenerators.generate_docx_proposal(data)
        return StreamingResponse(
            docx_buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename={ass.company_name.replace(' ', '_')}_AI_Pilot_Proposal.docx"
            },
        )
    elif doc_format.lower() == "pptx":
        pptx_buffer = DocumentGenerators.generate_pptx_deck(data)
        return StreamingResponse(
            pptx_buffer,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={
                "Content-Disposition": f"attachment; filename={ass.company_name.replace(' ', '_')}_Board_Presentation.pptx"
            },
        )
    else:
        raise HTTPException(
            status_code=400, detail="Invalid format. Use PDF, DOCX, or PPTX."
        )


@router.post("/demo", response_model=AssessmentResponse)
def create_walkthrough_workspace(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Auto-fills a complete, premium assessment with walkthrough client workspace data"""
    if not settings.ENABLE_DEMO_WORKSPACE:
        raise HTTPException(
            status_code=403,
            detail="Demo workspace seeding is disabled in this environment",
        )
    logger.info("Initializing Walkthrough Sample Workspace...")
    organization = get_or_create_default_organization(db, current_user)
    sample_client = (
        db.query(Client)
        .filter(
            Client.organization_id == organization.id,
            Client.name == "Apex Global Consulting Partners",
        )
        .first()
    )
    if not sample_client:
        sample_client = Client(
            organization_id=organization.id,
            name="Apex Global Consulting Partners",
            industry="Professional Services",
            company_size="100-500 employees",
            cloud_preference="Azure",
            compliance_requirements=["GDPR", "SOC2 Type II"],
        )
        db.add(sample_client)
        db.commit()
        db.refresh(sample_client)

    existing_sample = (
        db.query(Assessment)
        .filter(
            Assessment.user_id == current_user.id,
            Assessment.company_name == "Apex Global Consulting Partners",
        )
        .first()
    )
    if existing_sample:
        if existing_sample.client_summary is None:
            existing_sample.client_summary = (
                "Apex Global Consulting Partners has a credible near-term AI pilot opportunity in proposal "
                "automation and support triage. The most immediate value is in shortening response cycles "
                "without forcing a large platform replacement."
            )
        if existing_sample.data_justification is None:
            existing_sample.data_justification = (
                "Proposal content and operational knowledge exist across Salesforce, Excel, and SharePoint, "
                "but the data remains fragmented enough to limit immediate AI reuse without cleanup."
            )
        if existing_sample.process_justification is None:
            existing_sample.process_justification = (
                "Several workflows are highly repetitive and suitable for AI support, but they still rely on "
                "manual reviewer handoffs and informal execution patterns."
            )
        if existing_sample.integration_justification is None:
            existing_sample.integration_justification = (
                "Apex has mainstream enterprise systems in place, yet the operating model still depends on "
                "human coordination rather than clean middleware or API-driven orchestration."
            )
        if existing_sample.governance_justification is None:
            existing_sample.governance_justification = (
                "GDPR and SOC2 create a credible governance baseline, but AI-specific approval trails and "
                "output validation should still be tightened before expansion."
            )
        if existing_sample.security_justification is None:
            existing_sample.security_justification = (
                "The existing compliance posture supports a controlled pilot, especially because regulated "
                "document handling practices are already familiar to the organization."
            )
        if existing_sample.team_justification is None:
            existing_sample.team_justification = (
                "The business has clear appetite for AI pilots, but long-term success will depend on explicit "
                "ownership, rollout training, and stronger adoption processes."
            )
        if existing_sample.alignment_justification is None:
            existing_sample.alignment_justification = (
                "The selected AI opportunities map directly to faster proposal turnaround, improved support "
                "responsiveness, and reduced manual operations overhead."
            )
        if existing_sample.reviewer_notes is None:
            existing_sample.reviewer_notes = (
                "Sample client workspace pre-reviewed for consulting walkthroughs. Reconfirm integration assumptions "
                "and compliance posture against live environments."
            )
        if existing_sample.approval_status != "approved":
            existing_sample.approval_status = "approved"
        # Mark walkthrough seed as demo/simulated so internal demo export is gated correctly.
        if (existing_sample.analysis_mode or "").lower() != "demo":
            existing_sample.analysis_mode = "demo"
        if (existing_sample.model_run_status or "").lower() not in {
            "demo_simulated",
            "simulated",
        }:
            existing_sample.model_run_status = "demo_simulated"
        db.commit()
        db.refresh(existing_sample)
        return existing_sample

    # Create the assessment session
    ass = Assessment(
        user_id=current_user.id,
        client_id=sample_client.id,
        company_name="Apex Global Consulting Partners",
        industry="Professional Services",
        company_size="100-500 employees",
        departments=[
            "Operations",
            "Customer Support",
            "Sales & Pre-sales",
            "Compliance & Governance",
        ],
        current_tools=[
            "Salesforce",
            "Microsoft Excel",
            "Jira Service Desk",
            "SharePoint",
        ],
        cloud_preference="Azure",
        compliance_requirements=["GDPR", "SOC2 Type II"],
        main_business_goals="Automate redundant pre-sales proposal drafting and support ticket parsing to optimize service delivery speeds.",
        pain_points=[
            "Manual Process Overload",
            "Data Silos",
            "Slow Support Response Times",
        ],
        ai_goals=["Efficiency / Cost Reduction", "Enhanced Customer Experience"],
        # Scoring Metrics
        overall_score=62.0,
        automation_potential=28.0,
        confidence_score=92.0,
        status="completed",
        risk_level="Medium",
        analysis_mode="demo",
        model_run_status="demo_simulated",
        model_provider="demo",
        model_name="walkthrough-seed",
        scoring_method="demo_seed",
        # Breakdown
        data_readiness=55.0,
        data_justification="Proposal content and operational knowledge exist across Salesforce, Excel, and SharePoint, but the data remains fragmented enough to limit immediate AI reuse without cleanup.",
        process_readiness=60.0,
        process_justification="Several workflows are highly repetitive and suitable for AI support, but they still rely on manual reviewer handoffs and informal execution patterns.",
        integration_readiness=50.0,
        integration_justification="Apex has mainstream enterprise systems in place, yet the operating model still depends on human coordination rather than clean middleware or API-driven orchestration.",
        governance_readiness=68.0,
        governance_justification="GDPR and SOC2 create a credible governance baseline, but AI-specific approval trails and output validation should still be tightened before expansion.",
        security_readiness=72.0,
        security_justification="The existing compliance posture supports a controlled pilot, especially because regulated document handling practices are already familiar to the organization.",
        team_readiness=58.0,
        team_justification="The business has clear appetite for AI pilots, but long-term success will depend on explicit ownership, rollout training, and stronger adoption processes.",
        business_alignment=75.0,
        alignment_justification="The selected AI opportunities map directly to faster proposal turnaround, improved support responsiveness, and reduced manual operations overhead.",
        business_summary=(
            "Apex Global Consulting Partners is a mid-size professional services firm handling "
            "intensive support and operations workloads. Repeated workflows in data collation and "
            "proposal drafting slow operational response indexes. Embedding focused LLM classification "
            "agents represents a P1 high-impact transformation opportunity."
        ),
        client_summary=(
            "Apex Global Consulting Partners has a credible near-term AI pilot opportunity in proposal "
            "automation and support triage. The most immediate value is in shortening response cycles "
            "without forcing a large platform replacement."
        ),
        reviewer_notes=(
            "Sample client workspace pre-reviewed for consulting walkthroughs. Reconfirm integration assumptions "
            "and compliance posture against live environments."
        ),
        approval_status="approved",
        readiness_interpretation=(
            "With an overall AI readiness score of 62/100, Apex is well positioned to pilot operational AI agents. "
            "Security and Compliance metrics (72/100) are strong due to existing SOC2 policies. However, "
            "integration silos in legacy spreadsheets limit instant scale-out, calling for local middleware layers."
        ),
        recommended_first_pilot="Intelligent Pre-Sales Proposal Copilot",
        why_recommended_pilot="High transformation value, low implementation complexity, and fits the corporate priority of accelerating pre-sales proposal throughput.",
        expected_pilot_impact="Estimated to reduce first-draft proposal preparation from 2–3 days to under 30 minutes, with potential to improve reuse of approved content, consistency, and senior review efficiency based on observed workflow signals.",
    )
    db.add(ass)
    db.commit()
    db.refresh(ass)

    # Seed Bottlenecks
    bottlenecks = [
        ProcessBottleneck(
            assessment_id=ass.id,
            department="Sales & Pre-sales",
            process_name="Custom RFP / Proposal Compilation",
            bottleneck_description="Technical sales executives spend up to 12 hours manually copy-pasting references and templates from old bid documents.",
            ai_potential="High",
        ),
        ProcessBottleneck(
            assessment_id=ass.id,
            department="Customer Support",
            process_name="Manual Incident Ingestion",
            bottleneck_description="Triage engineers manually tag, catalog, and routes incoming client incident tickets, delaying response times.",
            ai_potential="High",
        ),
        ProcessBottleneck(
            assessment_id=ass.id,
            department="Operations",
            process_name="Excel Billing Reconciliation",
            bottleneck_description="Finance managers manually match billing columns from hourly logs in spreadsheets to ERP database sheets.",
            ai_potential="Medium",
        ),
    ]

    # Seed Use Cases
    use_cases = [
        AIUseCase(
            assessment_id=ass.id,
            department=normalize_department(
                "Intelligent Pre-Sales Proposal Copilot",
                "Intelligent solution drafting companion that pulls from verified proposal assets and past winning bid documents to build compliance-mapped proposal outlines.",
            ),
            use_case_name="Intelligent Pre-Sales Proposal Copilot",
            description="Intelligent solution drafting companion that pulls from verified proposal assets and past winning bid documents to build compliance-mapped proposal outlines.",
            value="High",
            complexity="Low",
            risk="Low",
            priority="P1",
            evidence="Recommended because sales teams report spending over 15 hours weekly on manual copy-pasting during RFP bid cycles.",
            confidence=92.0,
        ),
        AIUseCase(
            assessment_id=ass.id,
            department=normalize_department(
                "Autonomous Support Triage Router",
                "Implement an intelligent support ticket routing pipeline using LLM classification to auto-categorize and assign technician tags.",
            ),
            use_case_name="Autonomous Support Triage Router",
            description="Implement an intelligent support ticket routing pipeline using LLM classification to auto-categorize and assign technician tags.",
            value="High",
            complexity="Medium",
            risk="Low",
            priority="P1",
            evidence="Recommended because logs indicate ticket classification delays average 4 hours per incoming incident.",
            confidence=88.0,
        ),
        AIUseCase(
            assessment_id=ass.id,
            department=normalize_department(
                "Billing Excel Extraction Agent",
                "Deploy a layout-aware processing pipeline that matches invoice records against Excel spreadsheet columns.",
            ),
            use_case_name="Billing Excel Extraction Agent",
            description="Deploy a layout-aware processing pipeline that matches invoice records against Excel spreadsheet columns.",
            value="Medium",
            complexity="Low",
            risk="Low",
            priority="P2",
            evidence="Recommended because uploaded spreadsheets show repetitive billing entries mapped against old templates.",
            confidence=85.0,
        ),
        AIUseCase(
            assessment_id=ass.id,
            department=normalize_department(
                "Contract Audit Assistant",
                "An AI compliance auditor that automatically evaluates signed supplier agreements against GDPR mandates.",
            ),
            use_case_name="Contract Audit Assistant",
            description="An AI compliance auditor that automatically evaluates signed supplier agreements against GDPR mandates.",
            value="High",
            complexity="High",
            risk="Medium",
            priority="P2",
            evidence="Recommended because client maintains rigid GDPR compliance protocols for global operations.",
            confidence=82.0,
        ),
    ]

    # Seed Risks
    risks = [
        RiskRegister(
            assessment_id=ass.id,
            risk_name="Data Leaks in Proposal Generation",
            severity="Medium",
            recommendation="Establish strict local sanitization gates (regex scrubbers) to wipe customer names and proprietary figures prior to API submissions.",
            is_control_met=1,
        ),
        RiskRegister(
            assessment_id=ass.id,
            risk_name="Hallucinated Billing Records",
            severity="High",
            recommendation="Enforce a strict human-in-the-loop manual review interface for billing matches returning confidence values below 95%.",
            is_control_met=0,
        ),
    ]

    # Seed Roadmap
    roadmap = [
        RoadmapItem(
            assessment_id=ass.id,
            phase="30-Day",
            action_item="Launch Intelligent Pre-Sales Proposal Copilot MVP using winning contract vector stores.",
            expected_impact="Accelerates initial proposal drafting speeds by an estimated 65%.",
            confidence=90.0,
        ),
        RoadmapItem(
            assessment_id=ass.id,
            phase="60-Day",
            action_item="Integrate Support Triage Router into Jira Service Desk shadow staging queues.",
            expected_impact="Targeting up to 40% optimization of ticketing triage cycle times based on initial pilot benchmarks.",
            confidence=85.0,
        ),
        RoadmapItem(
            assessment_id=ass.id,
            phase="90-Day",
            action_item="Deploy Compliance Contract Auditor and enforce operational training for pre-sales teams.",
            expected_impact="Potential to save up to 10 staff hours weekly while supporting complete audit readiness.",
            confidence=92.0,
        ),
    ]

    # Seed Signals
    signals = [
        DocumentSignal(
            assessment_id=ass.id,
            source_file="Apex_Sales_Playbook.pdf",
            signal_type="RFP workflow",
            description="Identified 12-hour manual cycles spent on custom solution blocks in proposal compilation.",
            confidence=95.0,
        ),
        DocumentSignal(
            assessment_id=ass.id,
            source_file="Apex_Operations_Audit.txt",
            signal_type="Excel billing bottleneck",
            description="Found manual hourly log exports manually mapped to corporate billing templates.",
            confidence=90.0,
        ),
    ]

    for item in bottlenecks:
        db.add(item)
    for item in use_cases:
        db.add(item)
    for item in risks:
        db.add(item)
    for item in roadmap:
        db.add(item)
    for item in signals:
        db.add(item)

    db.commit()
    db.refresh(ass)
    return ass
