import os
from typing import ClassVar

from pydantic_settings import BaseSettings


def _parse_cors_origins() -> list[str]:
    raw_value = os.getenv("CORS_ORIGINS")
    if raw_value:
        return [origin.strip() for origin in raw_value.split(",") if origin.strip()]

    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]


def _default_cors_origins_raw() -> str:
    return ",".join(_parse_cors_origins())


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "yes", "on"}


class Settings(BaseSettings):
    # App General Config
    PROJECT_NAME: str = "AI Readiness Intelligence Studio"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    CORS_ORIGINS_RAW: str = os.getenv("CORS_ORIGINS", _default_cors_origins_raw())
    REQUIRE_POSTGRES: bool = _env_bool("REQUIRE_POSTGRES", "false")

    # Database CONFIG (Dual Mode Fallback)
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "aireadiness")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "db")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")

    @property
    def DATABASE_URL(self) -> str:
        """Return SQLAlchemy URL. Prefer explicit psycopg2 driver (installed via psycopg2-binary)."""
        database_url_override = os.getenv("DATABASE_URL")
        if database_url_override:
            # Normalize bare postgresql:// to psycopg2 so SQLAlchemy does not require psycopg v3.
            if database_url_override.startswith("postgresql://"):
                return (
                    "postgresql+psycopg2://"
                    + database_url_override[len("postgresql://") :]
                )
            if database_url_override.startswith("postgres://"):
                return (
                    "postgresql+psycopg2://"
                    + database_url_override[len("postgres://") :]
                )
            return database_url_override
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    SQLITE_URL: str = os.getenv("SQLITE_URL", "sqlite:///./aireadiness.db")

    # --- Model execution / safety ---
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY", "") or ""
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY", "") or ""
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    USE_OLLAMA: bool = _env_bool("USE_OLLAMA", "false")
    ALLOW_OLLAMA_FALLBACK: bool = _env_bool("ALLOW_OLLAMA_FALLBACK", "true")
    # When false, client documents are never sent to external providers.
    ALLOW_EXTERNAL_MODEL_PROVIDERS: bool = _env_bool(
        "ALLOW_EXTERNAL_MODEL_PROVIDERS", "true"
    )
    # Explicit demo simulation path — outputs must be marked as simulated.
    DEMO_MODE: bool = _env_bool("DEMO_MODE", "false")
    # Legacy heuristic fallback only when explicitly enabled (never silent in prod).
    ALLOW_HEURISTIC_FALLBACK: bool = _env_bool("ALLOW_HEURISTIC_FALLBACK", "false")
    # Shared demo credentials — disabled in production by default.
    ENABLE_DEMO_AUTH: bool = _env_bool(
        "ENABLE_DEMO_AUTH",
        "true" if os.getenv("ENVIRONMENT", "development") == "development" else "false",
    )
    ENABLE_DEMO_WORKSPACE: bool = _env_bool(
        "ENABLE_DEMO_WORKSPACE",
        "true" if os.getenv("ENVIRONMENT", "development") == "development" else "false",
    )

    LLM_TIMEOUT_SECONDS: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "45"))
    LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "2"))

    # Upload limits
    MAX_UPLOAD_FILES: int = int(os.getenv("MAX_UPLOAD_FILES", "12"))
    MAX_UPLOAD_FILE_BYTES: int = int(
        os.getenv("MAX_UPLOAD_FILE_BYTES", str(8 * 1024 * 1024))
    )
    ALLOWED_UPLOAD_EXTENSIONS: str = os.getenv(
        "ALLOWED_UPLOAD_EXTENSIONS", ".pdf,.docx,.txt,.md,.csv"
    )

    PRIMARY_LLM: str = os.getenv("PRIMARY_LLM", "openai/gpt-4o-mini")

    OLLAMA_REASONING_MODEL: str = os.getenv("OLLAMA_REASONING_MODEL", "qwen2.5:7b")
    OLLAMA_STRUCTURED_MODEL: str = os.getenv("OLLAMA_STRUCTURED_MODEL", "llama3:8b")
    OLLAMA_LIGHTWEIGHT_MODEL: str = os.getenv(
        "OLLAMA_LIGHTWEIGHT_MODEL", "phi3.5:latest"
    )
    OLLAMA_EMBEDDING_MODEL: str = os.getenv(
        "OLLAMA_EMBEDDING_MODEL", "nomic-embed-text:latest"
    )

    INSECURE_DEFAULT_SECRET: ClassVar[str] = "super-secret-key-change-in-production"

    @property
    def cors_origins(self) -> list[str]:
        raw_value = self.CORS_ORIGINS_RAW.strip()
        if not raw_value:
            return []
        return [origin.strip() for origin in raw_value.split(",") if origin.strip()]

    @property
    def allowed_upload_extensions(self) -> list[str]:
        return [
            ext.strip().lower()
            for ext in self.ALLOWED_UPLOAD_EXTENSIONS.split(",")
            if ext.strip()
        ]

    def validate_production_safety(self) -> None:
        if self.ENVIRONMENT.lower() not in {"production", "prod"}:
            return
        problems: list[str] = []
        if not self.SECRET_KEY or self.SECRET_KEY == self.INSECURE_DEFAULT_SECRET:
            problems.append(
                "SECRET_KEY must be set to a non-default value in production"
            )
        if self.ENABLE_DEMO_AUTH:
            problems.append("ENABLE_DEMO_AUTH must be false in production")
        if self.DEMO_MODE:
            problems.append("DEMO_MODE must be false in production")
        if self.ALLOW_HEURISTIC_FALLBACK:
            problems.append("ALLOW_HEURISTIC_FALLBACK must be false in production")
        if problems:
            raise RuntimeError(
                "Production safety checks failed: " + "; ".join(problems)
            )

    class Config:
        case_sensitive = True


settings = Settings()
