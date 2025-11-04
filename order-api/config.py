"""Application configuration settings."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Order Processing API"
    environment: Literal["local", "dev", "prod"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # AWS (Required)
    sqs_queue_url: str | None = Field(
        default=None,
        description="SQS queue URL (REQUIRED - set via SQS_QUEUE_URL env var)",
    )
    ddb_table: str | None = Field(
        default=None,
        description="DynamoDB table name (REQUIRED - set via DDB_TABLE env var)",
    )
    aws_endpoint_url: str | None = Field(
        default=None, description="AWS endpoint URL for local testing"
    )
    aws_access_key_id: str = Field(
        default="test", description="AWS access key ID"
    )
    aws_secret_access_key: str = Field(
        default="test", description="AWS secret access key"
    )
    aws_region: str = Field(default="us-east-1", description="AWS region")

    # Auth
    jwt_secret: str = Field(
        default="change-me-in-prod",
        description="JWT secret key (change in production!)",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expires_minutes: int = Field(
        default=60, ge=1, description="JWT token expiration in minutes"
    )

    # Rate limiting
    rate_limit: str = Field(
        default="100/minute", description="Rate limit per user"
    )


settings = Settings()
