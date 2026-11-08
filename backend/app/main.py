import logging

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api.assessment import router as assessment_router
from app.api.auth import router as auth_router
from app.api.clients import router as clients_router
from app.api.investment import router as investment_router
from app.core.config import settings
from app.core.database import Base, engine, ensure_runtime_schema, get_database_health

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AppMain")

# Fail closed on insecure production configuration.
try:
    settings.validate_production_safety()
except RuntimeError as safety_error:
    logger.error(str(safety_error))
    raise

# 1. Schema bootstrap
# PostgreSQL deployments must use Alembic (`alembic upgrade head`) — do not create_all
# ahead of migrations (that causes "table already exists" on fresh CI volumes).
# Local SQLite keeps create_all + ensure_runtime_schema for developer convenience.
try:
    if settings.REQUIRE_POSTGRES:
        logger.info(
            "REQUIRE_POSTGRES=true: skipping create_all; schema must come from Alembic."
        )
        ensure_runtime_schema()
    else:
        logger.info("Initializing database schemas (create_all + runtime patches)...")
        Base.metadata.create_all(bind=engine)
        ensure_runtime_schema()
        logger.info("Database schemas initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing database schemas: {e}")
    if settings.REQUIRE_POSTGRES:
        raise

# 2. Initialize FastAPI Application
app = FastAPI(
    title=settings.PROJECT_NAME, version="1.0.0", docs_url="/docs", redoc_url="/redoc"
)

# 3. Configure CORS Policies for local Next.js client
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Mount API Routes
app.include_router(
    auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"]
)
app.include_router(
    clients_router, prefix=f"{settings.API_V1_STR}/clients", tags=["Clients"]
)
app.include_router(
    assessment_router, prefix=f"{settings.API_V1_STR}/assessments", tags=["Assessments"]
)
app.include_router(
    investment_router,
    prefix=f"{settings.API_V1_STR}/assessments",
    tags=["Investment Intelligence"],
)


@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "tagline": "From business documents to AI opportunity roadmap in minutes.",
        "orchestrator": "LangGraph Stateful Engine Active",
    }


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/readyz")
def readyz():
    try:
        db_health = get_database_health()
        return {
            "status": "ready",
            "service": settings.PROJECT_NAME,
            "environment": settings.ENVIRONMENT,
            **db_health,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"Database readiness check failed: {exc}"
        ) from exc


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
