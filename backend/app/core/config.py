from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )

    PROJECT_NAME: str = "Budget App"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Railway automatically provides DATABASE_URL for PostgreSQL
    DATABASE_URL: str = "sqlite:///./budget_app.db"

    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Support Railway's frontend URL and localhost
    FRONTEND_URL: str = ""
    RAILWAY_PUBLIC_DOMAIN: str = ""

    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024
    UPLOAD_DIR: str = "./uploads"

    # Railway-specific settings
    PORT: int = 8000
    ENVIRONMENT: str = "development"

    @property
    def CORS_ORIGINS(self) -> List[str]:
        """Dynamically build CORS origins list"""
        origins = [
            "http://localhost:3000",
            "http://localhost:5173",
        ]

        # Add Railway URLs if set
        if self.FRONTEND_URL:
            origins.append(self.FRONTEND_URL)
        if self.RAILWAY_PUBLIC_DOMAIN:
            origins.append(f"https://{self.RAILWAY_PUBLIC_DOMAIN}")

        # In production, allow all origins (or be more restrictive)
        if self.ENVIRONMENT == "production":
            origins.append("*")

        return [o for o in origins if o]


settings = Settings()
