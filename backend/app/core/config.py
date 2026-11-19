import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Content Moderation with Explainable Hate Speech Detection"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Database
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "social_moderation_db"
    MEDIA_ROOT: Path = Path(__file__).resolve().parents[2] / "media_uploads"

    # JWT Security
    JWT_SECRET: str = "DEFAULT_INSECURE_SECRET_CHANGE_IN_PRODUCTION_ENV_MIN_32"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    # Initial Admin
    # Optional one-time bootstrap credentials. No account is created unless both are set.
    INITIAL_ADMIN_EMAIL: Optional[str] = None
    INITIAL_ADMIN_PASSWORD: Optional[str] = None

    # Browser origins allowed to use the HttpOnly session cookie.
    FRONTEND_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Model & Confidence Thresholds
    DEFAULT_MODEL_NAME: str = "distilbert-base-uncased-finetuned-sst-2-english"
    # Set only languages for which the configured classifier was trained and
    # evaluated. Detection alone does not imply moderation support.
    MODERATION_SUPPORTED_LANGUAGES: str = "en"
    CONFIDENCE_THRESHOLD_HIGH: float = 0.80
    CONFIDENCE_THRESHOLD_LOW: float = 0.50

    # Responsible AI
    EXPLAINABILITY_ENABLED: bool = True
    MAX_EXPLANATION_TOP_K: int = 5
    # Model artifacts are loaded from the local cache only by default. Operators
    # can provision weights ahead of deployment without sending runtime traffic
    # to a model hub.
    MODEL_LOCAL_FILES_ONLY: bool = True

    # Retention policies are enforced by the application cleanup task.
    AUDIT_RETENTION_DAYS: int = Field(default=365, ge=1, le=3650)
    RESOLVED_PRIVACY_REQUEST_RETENTION_DAYS: int = Field(default=365, ge=1, le=3650)
    PRIVACY_POLICY_VERSION: str = "1.0"

    # Legal / Contact Placeholders
    ORGANIZATION_NAME: str = "[PROJECT / ORGANIZATION NAME]"
    OFFICIAL_EMAIL: str = "[OFFICIAL EMAIL]"
    OFFICIAL_ADDRESS: str = "[OFFICIAL ADDRESS]"
    GRIEVANCE_CONTACT: str = "[GRIEVANCE CONTACT EMAIL]"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
