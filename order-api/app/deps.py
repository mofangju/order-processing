"""Dependencies and utilities for the application."""

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import TYPE_CHECKING

import boto3
from botocore.client import BaseClient
from fastapi import Request

from config import settings

if TYPE_CHECKING:
    from mypy_boto3_sqs import SQSClient
    from mypy_boto3_dynamodb import DynamoDBClient

# Request ID
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """Get the current request ID from context."""
    return request_id_ctx.get()


async def set_request_id(request: Request) -> str:
    """Set request ID from header or generate a new one."""
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request_id_ctx.set(rid)
    return rid


def get_sqs_client() -> BaseClient:
    """Get or create SQS client instance."""
    client_kwargs = {
        "aws_access_key_id": settings.aws_access_key_id,
        "aws_secret_access_key": settings.aws_secret_access_key,
        "region_name": settings.aws_region,
    }
    # Only include endpoint_url if it's provided (for local testing)
    if settings.aws_endpoint_url:
        client_kwargs["endpoint_url"] = settings.aws_endpoint_url
    return boto3.client("sqs", **client_kwargs)


def get_ddb_client() -> BaseClient:
    """Get or create DynamoDB client instance."""
    client_kwargs = {
        "aws_access_key_id": settings.aws_access_key_id,
        "aws_secret_access_key": settings.aws_secret_access_key,
        "region_name": settings.aws_region,
    }
    # Only include endpoint_url if it's provided (for local testing)
    if settings.aws_endpoint_url:
        client_kwargs["endpoint_url"] = settings.aws_endpoint_url
    return boto3.client("dynamodb", **client_kwargs)


def setup_logging() -> None:
    """Configure application logging with structured format."""
    logger = logging.getLogger("order-api")
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # Create structured formatter (JSON-like key-value pairs for better parsing)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False


# Initialize logger
setup_logging()
logger = logging.getLogger("order-api")
