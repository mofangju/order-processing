import uuid
import json
from datetime import datetime
from fastapi import FastAPI, Depends, Request, HTTPException, status
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from config import settings
from app.schemas import OrderIn, OrderOut, Token
from app.auth import create_access_token, get_current_user
from app.deps import set_request_id, get_request_id, get_sqs_client, get_ddb_client, logger

# App
app = FastAPI(
    title="Order API",
    description="High-throughput order ingestion with polling",
    version="2.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Rate limiter
limiter = Limiter(key_func=lambda request: get_current_user(request))
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    await set_request_id(request)
    response = await call_next(request)
    response.headers["X-Request-ID"] = get_request_id()
    return response

# Health
@app.get("/health")
async def health():
    return {"status": "healthy", "env": settings.environment}

@app.get("/ready")
async def ready():
    return {"status": "ready"}

# Auth
@app.post("/login", response_model=Token)
async def login(form_data: OrderIn):  # Reuse for demo
    token = create_access_token(form_data.user_id)
    return Token(access_token=token)

# Orders
@app.post("/orders", response_model=OrderOut, status_code=202)
@limiter.limit(settings.rate_limit)
async def create_order(
    request: Request,
    order_in: OrderIn,
    user_id: str = Depends(get_current_user),
    sqs = Depends(get_sqs_client),
    ddb = Depends(get_ddb_client)
):
    order_id = str(uuid.uuid4())
    requested_at = datetime.utcnow().isoformat() + "Z"

    # SQS
    try:
        sqs.send_message(
            QueueUrl=settings.sqs_queue_url,
            MessageBody=json.dumps({
                "order_id": order_id,
                "user_id": user_id,
                "amount": order_in.amount
            }),
            MessageGroupId="orders",
            MessageDeduplicationId=order_id
        )
    except Exception as e:
        logger.error(f"SQS error | order_id={order_id} | error={e}")
        raise HTTPException(status_code=502, detail="Queue unavailable")

    # Signed URL
    try:
        signed_url = ddb.generate_presigned_url(
            ClientMethod="get_item",
            Params={"TableName": settings.ddb_table, "Key": {"order_id": {"S": order_id}}},
            ExpiresIn=300,
            HttpMethod="GET"
        )
    except Exception as e:
        logger.error(f"DDB sign error | order_id={order_id} | error={e}")
        raise HTTPException(status_code=502, detail="DB unavailable")

    logger.info(f"Order created | order_id={order_id} | user_id={user_id} | amount={order_in.amount}")
    return OrderOut(
        order_id=order_id,
        poll_url=signed_url,
        requested_at=requested_at
    )