"""Application configuration using Pydantic Settings."""

from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "SourceCheck AI"
    APP_SECRET_KEY: str = "default_secret_key_change_in_production"

    # Authentication & JWT
    JWT_SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Google OAuth 2.0
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    @property
    def effective_jwt_secret(self) -> str:
        """Return the active JWT secret key, falling back to APP_SECRET_KEY."""
        return self.JWT_SECRET_KEY or self.APP_SECRET_KEY

    # Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"

    # CORS
    ALLOWED_ORIGINS: Union[str, List[str]] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # Database (PostgreSQL)
    DATABASE_URL: str = (
        "postgresql+asyncpg://sourcecheck:sourcecheck_password@localhost:5432/sourcecheck_db"
    )

    @property
    def sync_database_url(self) -> str:
        """Return synchronous database URL for Alembic migrations."""
        return (
            self.DATABASE_URL
            .replace("postgresql+asyncpg://", "postgresql+psycopg2://")
            .replace("sqlite+aiosqlite://", "sqlite://")
        )

    # Cache (Redis)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Vector DB (PostgreSQL + pgvector)
    VECTOR_DB_TYPE: str = "pgvector"
    EMBEDDING_PROVIDER: str = "openai"  # openai, mock, sentence-transformers
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIM: int = 1536
    EMBEDDING_BATCH_SIZE: int = 64
    VECTOR_SEARCH_TOP_K: int = 5
    VECTOR_SIMILARITY_THRESHOLD: float = 0.0

    # Reranker Settings (Cross-Encoder / Second-stage reranking)
    RERANKER_ENABLED: bool = True
    RERANKER_PROVIDER: str = "cross_encoder"  # cross_encoder, mock
    RERANKER_MODEL: str = "BAAI/bge-reranker-base"
    RERANKER_TOP_K: int = 5
    RERANKER_BATCH_SIZE: int = 16
    RERANKER_SCORE_THRESHOLD: Optional[float] = None



    # LLM Settings (Generation & Structured Output orchestration)
    LLM_PROVIDER: str = "openai"  # openai, anthropic, mock
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.0
    LLM_TIMEOUT_SECONDS: float = 30.0
    LLM_MAX_OUTPUT_TOKENS: int = 1500

    # Ingestion & Chunking Configuration (Centralized defaults, configurable per request)
    DEFAULT_CHUNK_SIZE: int = 500
    DEFAULT_CHUNK_OVERLAP: int = 50
    DEFAULT_SENTENCE_WINDOW_SIZE: int = 3
    MAX_UPLOAD_FILE_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB
    SUPPORTED_FILE_EXTENSIONS: List[str] = [".pdf", ".txt", ".docx"]


settings = Settings()
