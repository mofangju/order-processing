from typing import Literal

from pydantic import BaseModel, Field, PositiveInt


class OrderIn(BaseModel):
    user_id: str = Field(
        ..., min_length=1, max_length=50, description="Unique user identifier"
    )
    amount: PositiveInt = Field(..., description="Order amount in cents")


class OrderOut(BaseModel):
    order_id: str
    poll_url: str
    status: Literal["PENDING"] = "PENDING"
    requested_at: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
