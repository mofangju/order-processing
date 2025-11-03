import json

from app.deps import logger
from config import settings
from fastapi import HTTPException


def handle_order(ddb, order_id, order_in, sqs, user_id):
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
    
    return signed_url
