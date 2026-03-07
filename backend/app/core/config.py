from pydantic_settings import BaseSettings
from typing import Optional, List
import os


class Settings(BaseSettings):
    PROJECT_NAME: str = "Budget App"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Railway automatically provides DATABASE_URL for PostgreSQL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./budget_app.db")

    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Support Railway's frontend URL and localhost
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        os.getenv("FRONTEND_URL", ""),
        os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
    ]

    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024
    UPLOAD_DIR: str = "./uploads"

    # Railway-specific settings
    PORT: int = int(os.getenv("PORT", "8000"))
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    class Config:
        env_file = ".env"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Filter out empty CORS origins
        self.CORS_ORIGINS = [origin for origin in self.CORS_ORIGINS if origin]
        # Add wildcard for Railway preview deployments if needed
        if self.ENVIRONMENT == "production":
            self.CORS_ORIGINS.append("*")


settings = Settings()
