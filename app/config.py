"""Application configuration management."""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    db_url: str = "sqlite:///./data/demo.db"

    # Authentication
    admin_username: str = "admin"
    admin_password: str = "retailai2025"
    secret_key: str = "change-this-in-production-please"

    # Application
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True

    # Logging
    log_level: str = "INFO"

    # File Upload
    max_upload_size_mb: int = 50
    upload_dir: str = "data/uploads"

    # OCR
    tesseract_cmd: Optional[str] = None
    ocr_language: str = "tur"

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 60

    # Cache (Redis)
    redis_enabled: bool = False
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 300

    # Security
    cors_origins: str = "*"
    allowed_hosts: str = "*"
    https_only: bool = False

    # Monitoring
    sentry_dsn: Optional[str] = None
    analytics_enabled: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
