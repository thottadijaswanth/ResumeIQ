from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Resume Analyzer & Job Matcher"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./resumeiq.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security & Auth
    SECRET_KEY: str = "dev-super-secret-jwt-key-change-in-production-1234567890"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # AI Configuration
    AI_PROVIDER: str = "mock"  # "ollama" | "openai" | "mock"
    AI_API_KEY: Optional[str] = None  # Legacy alias for OPENAI_API_KEY
    AI_MODEL: Optional[str] = None  # Legacy override if OPENAI_MODEL not specified

    # Local Ollama Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:1.7b"
    OLLAMA_TEMPERATURE: float = 0.0
    OLLAMA_TIMEOUT: float = 240.0
    OLLAMA_MAX_RETRIES: int = 1
    OLLAMA_THINK: Optional[bool] = False

    # Cloud OpenAI-Compatible Configuration
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_TEMPERATURE: float = 0.1
    OPENAI_TIMEOUT: float = 60.0
    OPENAI_MAX_RETRIES: int = 2

    # Fallback Behavior (disabled by default so local AI never silently fakes mock results)
    AI_FALLBACK_ENABLED: bool = False
    AI_FALLBACK_PROVIDER: Optional[str] = None
    AI_ALLOW_CLOUD_FALLBACK: bool = False

    # High-Throughput Screening & Reranking Configuration
    MATCHING_TOP_K: int = 100
    AI_RERANK_TOP_K: int = 20
    MAX_CONCURRENT_RESUME_PROCESSING: int = 4
    AI_RERANK_MAX_TOKENS: int = 450
    UPLOAD_BATCH_SIZE: int = 50

    # Embeddings Configuration
    EMBEDDING_PROVIDER: str = "local"  # "local" | "openai" | "mock"
    EMBEDDING_BASE_URL: Optional[str] = None
    EMBEDDING_API_KEY: Optional[str] = None
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    EMBEDDING_TIMEOUT: float = 30.0

    def get_openai_api_key(self) -> Optional[str]:
        return self.OPENAI_API_KEY or self.AI_API_KEY

    def get_openai_model(self) -> str:
        if self.OPENAI_MODEL and self.OPENAI_MODEL != "gpt-4o-mini":
            return self.OPENAI_MODEL
        return self.AI_MODEL or self.OPENAI_MODEL

    def get_embedding_api_key(self) -> Optional[str]:
        return self.EMBEDDING_API_KEY or self.get_openai_api_key()

    def get_embedding_base_url(self) -> str:
        return (self.EMBEDDING_BASE_URL or self.OPENAI_BASE_URL).rstrip("/")

    # Scoring Weights (must sum to 1.0)
    WEIGHT_SKILLS: float = 0.35
    WEIGHT_EXPERIENCE: float = 0.20
    WEIGHT_SEMANTIC: float = 0.20
    WEIGHT_KEYWORDS: float = 0.15
    WEIGHT_EDUCATION: float = 0.10

    # Uploads
    MAX_UPLOAD_SIZE_MB: int = 5
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "docx"]

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    CORS_ORIGIN_REGEX: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=(str(_ROOT_ENV), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
    )


settings = Settings()

