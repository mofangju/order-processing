"""Main FastAPI application module."""

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Callable

from botocore.client import BaseClient
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.auth import create_access_token, get_current_user
from app.deps import (
    get_ddb_client,
    get_request_id,
    get_sqs_client,
    logger,
    set_request_id,
)
from app.handler import handle_order
from app.schemas import OrderIn, OrderOut, Token
from config import settings


def validate_required_settings() -> None:
    """Validate that all required settings are configured at startup."""
    missing_settings = []
    
    if not settings.sqs_queue_url:
        missing_settings.append("SQS_QUEUE_URL")
    
    if not settings.ddb_table:
        missing_settings.append("DDB_TABLE")
    
    if missing_settings:
        error_msg = (
            f"Missing required configuration: {', '.join(missing_settings)}. "
            "Please set these environment variables before starting the application."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("Starting Order API...")
    try:
        validate_required_settings()
        logger.info("Configuration validation passed")
    except ValueError as e:
        logger.critical(f"Configuration validation failed: {e}")
        raise
    yield
    # Shutdown
    logger.info("Shutting down Order API...")


# App
app = FastAPI(
    title="Order API",
    description="High-throughput order ingestion with polling",
    version="2.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


def get_user_id_for_rate_limit(request: Request) -> str:
    """
    Get user ID for rate limiting.

    Falls back to IP address if user is not authenticated.
    """
    try:
        return get_remote_address(request)
    except Exception:
        # Fallback to a default value if IP cannot be determined
        return "unknown"


# Rate limiter
limiter = Limiter(key_func=get_user_id_for_rate_limit)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Middleware
@app.middleware("http")
async def add_request_id_middleware(
    request: Request, call_next: Callable[[Request], Any]
) -> Response:
    """Add request ID to context and response headers."""
    await set_request_id(request)
    response = await call_next(request)
    response.headers["X-Request-ID"] = get_request_id()
    return response


# Health
@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "env": settings.environment}


@app.get("/ready")
async def ready() -> dict[str, str]:
    """
    Readiness check endpoint.
    
    Validates that required services are configured.
    """
    missing_config = []
    if not settings.sqs_queue_url:
        missing_config.append("sqs_queue_url")
    if not settings.ddb_table:
        missing_config.append("ddb_table")
    
    if missing_config:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not ready: missing configuration for {', '.join(missing_config)}",
        )
    
    return {"status": "ready"}


# Auth
@app.post("/login", response_model=Token)
async def login(form_data: OrderIn) -> Token:
    """
    Login endpoint to obtain JWT token.

    For demo purposes, reuses OrderIn schema.
    In production, use a dedicated Login schema.
    
    Note: This is a simplified authentication flow for demonstration.
    In production, implement proper password verification and user management.
    """
    token = create_access_token(form_data.user_id)
    logger.info(f"Token generated for user | user_id={form_data.user_id}")
    return Token(access_token=token)


# Orders
@app.post("/orders", response_model=OrderOut, status_code=202)
@limiter.limit(settings.rate_limit)
async def create_order(
    request: Request,
    order_in: OrderIn,
    user_id: str = Depends(get_current_user),
    sqs: BaseClient = Depends(get_sqs_client),
    ddb: BaseClient = Depends(get_ddb_client),
) -> OrderOut:
    """
    Create a new order.

    Returns a 202 Accepted response with a polling URL.
    """
    order_id = str(uuid.uuid4())
    requested_at = datetime.now(timezone.utc).isoformat()

    signed_url = handle_order(ddb, order_id, order_in, sqs, user_id)

    logger.info(
        f"Order created | order_id={order_id} | user_id={user_id} | "
        f"amount={order_in.amount}"
    )
    return OrderOut(
        order_id=order_id, poll_url=signed_url, requested_at=requested_at
    )
