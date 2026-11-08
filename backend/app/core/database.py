import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Database")

Base = declarative_base()

# Global engine and session makers
engine = None
SessionLocal = None


def init_db():
    global engine, SessionLocal

    # Try PostgreSQL first
    try:
        logger.info(
            f"Attempting connection to PostgreSQL at {settings.POSTGRES_HOST}..."
        )
        postgres_url = settings.DATABASE_URL
        # Explicit connect_timeout only for libpq/psycopg2 drivers.
        connect_args = {}
        if "+psycopg2" in postgres_url or postgres_url.startswith("postgresql"):
            connect_args = {"connect_timeout": 3}
        engine = create_engine(postgres_url, connect_args=connect_args)
        # Test connection
        with engine.connect():
            logger.info(
                "Successfully connected to database dialect=%s driver=%s",
                engine.url.get_backend_name(),
                engine.url.drivername,
            )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    except Exception as e:
        if settings.REQUIRE_POSTGRES:
            logger.error(
                "PostgreSQL connection failed while REQUIRE_POSTGRES=true. Refusing SQLite fallback."
            )
            raise
        logger.warning(f"PostgreSQL connection failed ({e}). Falling back to SQLite...")
        try:
            sqlite_url = settings.SQLITE_URL
            engine = create_engine(
                sqlite_url, connect_args={"check_same_thread": False}
            )
            logger.info(
                f"Successfully initialized SQLite database fallback at: {sqlite_url}"
            )
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        except Exception as sqle:
            logger.error(f"SQLite initialization also failed! {sqle}")
            raise


# Initialize DB on import/startup
init_db()


def get_database_health() -> dict:
    if engine is None:
        raise RuntimeError("Database engine not initialized")
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    return {
        "database": "ok",
        "dialect": engine.url.get_backend_name(),
        "driver": engine.url.drivername,
    }


def get_db():
    if SessionLocal is None:
        raise RuntimeError("Database session not initialized")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_runtime_schema():
    """
    Applies tiny compatibility fixes for existing local databases when the ORM evolves
    but there is no migration framework in the repo yet.
    """
    inspector = inspect(engine)
    if "assessments" not in inspector.get_table_names():
        return

    assessment_columns = {
        column["name"] for column in inspector.get_columns("assessments")
    }
    if "user_id" not in assessment_columns:
        logger.info(
            "Adding missing assessments.user_id column for authenticated ownership..."
        )
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE assessments ADD COLUMN user_id INTEGER"))

    if "client_id" not in assessment_columns:
        logger.info(
            "Adding missing assessments.client_id column for client workspace mapping..."
        )
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE assessments ADD COLUMN client_id INTEGER"))

    if "client_summary" not in assessment_columns:
        logger.info(
            "Adding missing assessments.client_summary column for client-facing summaries..."
        )
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE assessments ADD COLUMN client_summary TEXT"))

    if "reviewer_notes" not in assessment_columns:
        logger.info(
            "Adding missing assessments.reviewer_notes column for internal consultant notes..."
        )
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE assessments ADD COLUMN reviewer_notes TEXT"))

    if "approval_status" not in assessment_columns:
        logger.info(
            "Adding missing assessments.approval_status column for review workflow..."
        )
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE assessments ADD COLUMN approval_status VARCHAR DEFAULT 'draft'"
                )
            )

    phase1_assessment_columns = {
        "scoring_rubric_version": "ALTER TABLE assessments ADD COLUMN scoring_rubric_version VARCHAR",
        "scoring_method": "ALTER TABLE assessments ADD COLUMN scoring_method VARCHAR",
        "dimension_score_details": "ALTER TABLE assessments ADD COLUMN dimension_score_details JSON",
        "automation_potential_basis": "ALTER TABLE assessments ADD COLUMN automation_potential_basis VARCHAR",
        "analysis_mode": "ALTER TABLE assessments ADD COLUMN analysis_mode VARCHAR",
        "model_provider": "ALTER TABLE assessments ADD COLUMN model_provider VARCHAR",
        "model_name": "ALTER TABLE assessments ADD COLUMN model_name VARCHAR",
        "model_run_status": "ALTER TABLE assessments ADD COLUMN model_run_status VARCHAR",
        "model_error": "ALTER TABLE assessments ADD COLUMN model_error TEXT",
        "evidence_package": "ALTER TABLE assessments ADD COLUMN evidence_package JSON",
        "insufficient_evidence": "ALTER TABLE assessments ADD COLUMN insufficient_evidence INTEGER DEFAULT 0",
    }
    for column_name, ddl in phase1_assessment_columns.items():
        if column_name not in assessment_columns:
            logger.info("Adding missing assessments.%s column...", column_name)
            with engine.begin() as conn:
                conn.execute(text(ddl))

    if "document_signals" in inspector.get_table_names():
        signal_columns = {
            column["name"] for column in inspector.get_columns("document_signals")
        }
        phase1_signal_columns = {
            "document_id": "ALTER TABLE document_signals ADD COLUMN document_id VARCHAR",
            "excerpt": "ALTER TABLE document_signals ADD COLUMN excerpt TEXT",
            "page_or_section": "ALTER TABLE document_signals ADD COLUMN page_or_section VARCHAR",
            "evidence_tier": "ALTER TABLE document_signals ADD COLUMN evidence_tier VARCHAR",
            "evidence_id": "ALTER TABLE document_signals ADD COLUMN evidence_id VARCHAR",
        }
        for column_name, ddl in phase1_signal_columns.items():
            if column_name not in signal_columns:
                logger.info("Adding missing document_signals.%s column...", column_name)
                with engine.begin() as conn:
                    conn.execute(text(ddl))

    for table_name in ("process_bottlenecks", "ai_use_cases", "risk_registers"):
        if table_name not in inspector.get_table_names():
            continue
        cols = {column["name"] for column in inspector.get_columns(table_name)}
        if "evidence_refs" not in cols:
            logger.info("Adding missing %s.evidence_refs column...", table_name)
            with engine.begin() as conn:
                conn.execute(
                    text(f"ALTER TABLE {table_name} ADD COLUMN evidence_refs JSON")
                )

    # Phase 3 workspace columns (local SQLite convenience; Postgres uses Alembic).
    phase3_assessment_columns = {
        "organization_id": "ALTER TABLE assessments ADD COLUMN organization_id INTEGER",
        "business_unit": "ALTER TABLE assessments ADD COLUMN business_unit VARCHAR",
        "workflow_status": "ALTER TABLE assessments ADD COLUMN workflow_status VARCHAR",
        "locked_for_delivery": "ALTER TABLE assessments ADD COLUMN locked_for_delivery INTEGER DEFAULT 0",
        "workflow_approved_at": "ALTER TABLE assessments ADD COLUMN workflow_approved_at DATETIME",
        "workflow_approved_by_user_id": "ALTER TABLE assessments ADD COLUMN workflow_approved_by_user_id INTEGER",
        "proposal_package": "ALTER TABLE assessments ADD COLUMN proposal_package JSON",
        "sow_package": "ALTER TABLE assessments ADD COLUMN sow_package JSON",
        "fee_estimate": "ALTER TABLE assessments ADD COLUMN fee_estimate JSON",
        "proposal_locked": "ALTER TABLE assessments ADD COLUMN proposal_locked INTEGER DEFAULT 0",
        "proposal_approved_at": "ALTER TABLE assessments ADD COLUMN proposal_approved_at DATETIME",
    }
    for column_name, ddl in phase3_assessment_columns.items():
        if column_name not in assessment_columns:
            logger.info("Adding missing assessments.%s column...", column_name)
            with engine.begin() as conn:
                conn.execute(text(ddl))

    if "organizations" in inspector.get_table_names():
        org_columns = {
            column["name"] for column in inspector.get_columns("organizations")
        }
        phase3_org_columns = {
            "workspace_type": "ALTER TABLE organizations ADD COLUMN workspace_type VARCHAR DEFAULT 'consulting_agency'",
            "brand_display_name": "ALTER TABLE organizations ADD COLUMN brand_display_name VARCHAR",
            "brand_logo_url": "ALTER TABLE organizations ADD COLUMN brand_logo_url VARCHAR",
            "brand_primary_color": "ALTER TABLE organizations ADD COLUMN brand_primary_color VARCHAR",
            "brand_secondary_color": "ALTER TABLE organizations ADD COLUMN brand_secondary_color VARCHAR",
            "brand_contact_email": "ALTER TABLE organizations ADD COLUMN brand_contact_email VARCHAR",
            "brand_contact_phone": "ALTER TABLE organizations ADD COLUMN brand_contact_phone VARCHAR",
            "brand_footer_text": "ALTER TABLE organizations ADD COLUMN brand_footer_text TEXT",
        }
        for column_name, ddl in phase3_org_columns.items():
            if column_name not in org_columns:
                logger.info("Adding missing organizations.%s column...", column_name)
                with engine.begin() as conn:
                    conn.execute(text(ddl))

    if "clients" in inspector.get_table_names():
        client_columns = {column["name"] for column in inspector.get_columns("clients")}
        phase3_client_columns = {
            "business_unit": "ALTER TABLE clients ADD COLUMN business_unit VARCHAR",
            "engagement_status": "ALTER TABLE clients ADD COLUMN engagement_status VARCHAR",
            "assigned_consultant_user_id": "ALTER TABLE clients ADD COLUMN assigned_consultant_user_id INTEGER",
            "consultant_notes": "ALTER TABLE clients ADD COLUMN consultant_notes TEXT",
            "proposal_package": "ALTER TABLE clients ADD COLUMN proposal_package JSON",
            "sow_package": "ALTER TABLE clients ADD COLUMN sow_package JSON",
            "fee_estimate": "ALTER TABLE clients ADD COLUMN fee_estimate JSON",
        }
        for column_name, ddl in phase3_client_columns.items():
            if column_name not in client_columns:
                logger.info("Adding missing clients.%s column...", column_name)
                with engine.begin() as conn:
                    conn.execute(text(ddl))

    if "users" in inspector.get_table_names():
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "full_name" not in user_columns:
            logger.info("Adding missing users.full_name column...")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN full_name VARCHAR"))

    if "organization_memberships" in inspector.get_table_names():
        membership_columns = {
            column["name"]
            for column in inspector.get_columns("organization_memberships")
        }
        if "authorized_client_ids" not in membership_columns:
            logger.info(
                "Adding missing organization_memberships.authorized_client_ids column..."
            )
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE organization_memberships "
                        "ADD COLUMN authorized_client_ids JSON"
                    )
                )
