"""Pydantic models for request/response schemas."""

from typing import Literal

from pydantic import BaseModel, Field, PositiveInt


class OrderIn(BaseModel):
    """Input schema for order creation."""

    user_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Unique user identifier",
        examples=["user123"],
    )
    amount: PositiveInt = Field(
        ...,
        description="Order amount in cents",
        examples=[1000],
        gt=0,
    )


class OrderOut(BaseModel):
    """Output schema for order creation response."""

    order_id: str = Field(..., description="Unique order identifier")
    poll_url: str = Field(..., description="Signed URL for polling order status")
    status: Literal["PENDING"] = Field(
        default="PENDING", description="Order status (always PENDING initially)"
    )
    requested_at: str = Field(
        ..., description="ISO 8601 timestamp of order creation in UTC"
    )


class Token(BaseModel):
    """JWT token response schema."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(
        default="bearer", description="Token type (always 'bearer')"
    )
