import os
from pydantic_settings import BaseSettings
from typing import List, Optional


def _parse_cors_origins() -> List[str]:
    raw_value = os.getenv("CORS_ORIGINS")
    if raw_value:
        return [origin.strip() for origin in raw_value.split(",") if origin.strip()]

    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]


class Settings(BaseSettings):
    # App General Config
    PROJECT_NAME: str = "AI Readiness Intelligence Studio"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    CORS_ORIGINS: List[str] = _parse_cors_origins()
    REQUIRE_POSTGRES: bool = os.getenv("REQUIRE_POSTGRES", "false").lower() == "true"

    # Database CONFIG (Dual Mode Fallback)
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "aireadiness")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "db")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")

    # Base connection URLs
    @property
    def DATABASE_URL(self) -> str:
        database_url_override = os.getenv("DATABASE_URL")
        if database_url_override:
            return database_url_override
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    SQLITE_URL: str = os.getenv("SQLITE_URL", "sqlite:///./aireadiness.db")

    # LLM Settings
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY", "")
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    USE_OLLAMA: bool = os.getenv("USE_OLLAMA", "false").lower() == "true"

    # Model preferences
    PRIMARY_LLM: str = "groq/llama-3.3-70b-versatile"

    # Ollama Catalog mappings
    OLLAMA_REASONING_MODEL: str = os.getenv(
        "OLLAMA_REASONING_MODEL", "qwen3.5:9b"
    )  # fallback: llama3:8b
    OLLAMA_STRUCTURED_MODEL: str = os.getenv(
        "OLLAMA_STRUCTURED_MODEL", "qwen2.5-coder:14b"
    )
    OLLAMA_LIGHTWEIGHT_MODEL: str = os.getenv(
        "OLLAMA_LIGHTWEIGHT_MODEL", "phi3.5:latest"
    )

    # Embeddings config
    OLLAMA_EMBEDDING_MODEL: str = os.getenv(
        "OLLAMA_EMBEDDING_MODEL", "nomic-embed-text:latest"
    )  # fallback: qwen3-embedding:8b

    class Config:
        case_sensitive = True


settings = Settings()
