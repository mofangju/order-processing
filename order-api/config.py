from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    app_name: str = "Order Processing API"
    environment: Literal["local", "dev", "prod"] = "local"
    log_level: str = "INFO"

    # AWS
    sqs_queue_url: str | None = None
    ddb_table: str | None = None
    aws_endpoint_url: str | None = None

    # Auth
    jwt_secret: str = "change-me-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60

    # Rate limiting
    rate_limit: str = "100/minute"

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
