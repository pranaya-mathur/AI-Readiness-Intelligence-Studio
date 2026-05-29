import logging
import uvicorn
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base, ensure_runtime_schema, get_database_health
from app.api.auth import router as auth_router
from app.api.clients import router as clients_router
from app.api.assessment import router as assessment_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AppMain")

# 1. Automatically create database tables (SQLite fallback or PostgreSQL)
try:
    logger.info("Initializing database schemas...")
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema()
    logger.info("Database schemas initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing database schemas: {e}")

# 2. Initialize FastAPI Application
app = FastAPI(
    title=settings.PROJECT_NAME, version="1.0.0", docs_url="/docs", redoc_url="/redoc"
)

# 3. Configure CORS Policies for local Next.js client
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
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
