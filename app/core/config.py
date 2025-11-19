"""
Core configuration module using Pydantic Settings.
Supports environment variables and .env files.
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PostgresDsn


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )

    # Application
    app_name: str = Field(default="Retail AI MVP", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://retail_user:retail_password@localhost:5432/retail_mvp",
        alias="DATABASE_URL"
    )
    db_echo: bool = Field(default=False, alias="DB_ECHO")
    db_pool_size: int = Field(default=20, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=40, alias="DB_MAX_OVERFLOW")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_cache_ttl: int = Field(default=3600, alias="REDIS_CACHE_TTL")

    # JWT Authentication
    jwt_secret_key: str = Field(
        default="your-secret-key-change-this-in-production",
        alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=30, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(default=7, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS")

    # Security
    bcrypt_rounds: int = Field(default=12, alias="BCRYPT_ROUNDS")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        alias="CORS_ORIGINS"
    )

    # File Upload
    upload_dir: str = Field(default="./uploads", alias="UPLOAD_DIR")
    max_upload_size: int = Field(default=10 * 1024 * 1024, alias="MAX_UPLOAD_SIZE")  # 10MB
    allowed_extensions: set[str] = Field(
        default={"jpg", "jpeg", "png", "pdf"},
        alias="ALLOWED_EXTENSIONS"
    )

    # OCR Settings
    ocr_language: str = Field(default="tur+eng", alias="OCR_LANGUAGE")
    ocr_confidence_threshold: float = Field(default=0.60, alias="OCR_CONFIDENCE_THRESHOLD")

    # Email Settings
    smtp_host: Optional[str] = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: Optional[str] = Field(default=None, alias="SMTP_USER")
    smtp_password: Optional[str] = Field(default=None, alias="SMTP_PASSWORD")
    smtp_from_email: str = Field(default="noreply@retailai.com", alias="SMTP_FROM_EMAIL")
    smtp_from_name: str = Field(default="Retail AI", alias="SMTP_FROM_NAME")

    # SendGrid (alternative to SMTP)
    sendgrid_api_key: Optional[str] = Field(default=None, alias="SENDGRID_API_KEY")

    # Stock Management
    default_critical_stock_level: int = Field(default=10, alias="DEFAULT_CRITICAL_STOCK_LEVEL")
    stock_alert_check_interval: int = Field(default=3600, alias="STOCK_ALERT_CHECK_INTERVAL")  # seconds

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: str = Field(default="./logs/app.log", alias="LOG_FILE")
    log_max_bytes: int = Field(default=10 * 1024 * 1024, alias="LOG_MAX_BYTES")  # 10MB
    log_backup_count: int = Field(default=5, alias="LOG_BACKUP_COUNT")

    # Celery (Task Queue)
    celery_broker_url: str = Field(default="redis://localhost:6379/1", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/2", alias="CELERY_RESULT_BACKEND")

    # S3 / Object Storage
    s3_endpoint_url: Optional[str] = Field(default=None, alias="S3_ENDPOINT_URL")
    s3_access_key: Optional[str] = Field(default=None, alias="S3_ACCESS_KEY")
    s3_secret_key: Optional[str] = Field(default=None, alias="S3_SECRET_KEY")
    s3_bucket_name: str = Field(default="retail-ai-uploads", alias="S3_BUCKET_NAME")
    s3_region: str = Field(default="us-east-1", alias="S3_REGION")

    # Monitoring
    sentry_dsn: Optional[str] = Field(default=None, alias="SENTRY_DSN")
    enable_metrics: bool = Field(default=True, alias="ENABLE_METRICS")

    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")
    rate_limit_burst: int = Field(default=10, alias="RATE_LIMIT_BURST")


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Dependency injection for FastAPI."""
    return settings
