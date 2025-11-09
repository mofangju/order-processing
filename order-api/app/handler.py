"""Order handling business logic."""

import json

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException, status

from app.deps import logger
from app.schemas import OrderIn
from config import settings


def handle_order(
    ddb: BaseClient,
    order_id: str,
    order_in: OrderIn,
    sqs: BaseClient,
    user_id: str,
) -> str:
    """
    Process an order by sending it to SQS and generating a polling URL.

    Args:
        ddb: DynamoDB client instance
        order_id: Unique order identifier
        order_in: Order input data
        sqs: SQS client instance
        user_id: User identifier

    Returns:
        Signed URL for polling order status

    Raises:
        HTTPException: If SQS or DynamoDB operations fail
    """
    if not settings.sqs_queue_url:
        logger.error("SQS queue URL not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Queue service not configured",
        )

    # SQS
    try:
        sqs.send_message(
            QueueUrl=settings.sqs_queue_url,
            MessageBody=json.dumps(
                {
                    "order_id": order_id,
                    "user_id": user_id,
                    "amount": order_in.amount,
                }
            ),
            MessageGroupId=user_id,
            MessageDeduplicationId=order_id,
        )
        logger.info(
            f"Order sent to queue | order_id={order_id} | user_id={user_id} | amount={order_in.amount}"
        )
    except (BotoCoreError, ClientError) as e:
        logger.error(
            f"SQS error | order_id={order_id} | error={str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Queue service unavailable",
        ) from e
    except Exception as e:
        logger.error(
            f"Unexpected SQS error | order_id={order_id} | error={str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e

    if not settings.ddb_table:
        logger.error("DynamoDB table not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service not configured",
        )

    # Signed URL
    try:
        signed_url = ddb.generate_presigned_url(
            ClientMethod="get_item",
            Params={
                "TableName": settings.ddb_table,
                "Key": {"order_id": {"S": order_id}},
            },
            ExpiresIn=300,
            HttpMethod="GET",
        )
        logger.debug(f"Generated signed URL | order_id={order_id}")
    except (BotoCoreError, ClientError) as e:
        logger.error(
            f"DDB sign error | order_id={order_id} | error={str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Database service unavailable",
        ) from e
    except Exception as e:
        logger.error(
            f"Unexpected DDB error | order_id={order_id} | error={str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e

    return signed_url
