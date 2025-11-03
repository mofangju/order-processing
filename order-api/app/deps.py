import uuid
import logging
from contextvars import ContextVar
from fastapi import Request, Depends
import boto3
from config import settings

# Request ID
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")

def get_request_id() -> str:
    return request_id_ctx.get()

async def set_request_id(request: Request):
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request_id_ctx.set(rid)
    return rid

# AWS Clients
def get_sqs_client():
    return boto3.client(
        "sqs",
        endpoint_url=settings.aws_endpoint_url,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1"
    )

def get_ddb_client():
    return boto3.client(
        "dynamodb",
        endpoint_url=settings.aws_endpoint_url,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1"
    )

# Logger
logger = logging.getLogger("order-api")