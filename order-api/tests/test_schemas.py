"""Tests for Pydantic schema validation."""

import pytest
from pydantic import ValidationError

from app.schemas import OrderIn, OrderOut, Token


def test_order_in_valid():
    """Test OrderIn with valid data."""
    order = OrderIn(user_id="user123", amount=1000)
    assert order.user_id == "user123"
    assert order.amount == 1000


def test_order_in_minimum_user_id():
    """Test OrderIn with minimum valid user_id length."""
    order = OrderIn(user_id="a", amount=1)
    assert order.user_id == "a"
    assert order.amount == 1


def test_order_in_maximum_user_id():
    """Test OrderIn with maximum valid user_id length."""
    max_user_id = "a" * 50
    order = OrderIn(user_id=max_user_id, amount=1)
    assert order.user_id == max_user_id


def test_order_in_user_id_too_long():
    """Test OrderIn with user_id exceeding max length."""
    long_user_id = "a" * 51
    with pytest.raises(ValidationError):
        OrderIn(user_id=long_user_id, amount=1)


def test_order_in_user_id_empty():
    """Test OrderIn with empty user_id."""
    with pytest.raises(ValidationError):
        OrderIn(user_id="", amount=1)


def test_order_in_amount_zero():
    """Test OrderIn with amount of zero."""
    with pytest.raises(ValidationError):
        OrderIn(user_id="user123", amount=0)


def test_order_in_amount_negative():
    """Test OrderIn with negative amount."""
    with pytest.raises(ValidationError):
        OrderIn(user_id="user123", amount=-1)


def test_order_in_amount_minimum():
    """Test OrderIn with minimum valid amount."""
    order = OrderIn(user_id="user123", amount=1)
    assert order.amount == 1


def test_order_in_missing_user_id():
    """Test OrderIn with missing user_id."""
    with pytest.raises(ValidationError):
        OrderIn(amount=1000)


def test_order_in_missing_amount():
    """Test OrderIn with missing amount."""
    with pytest.raises(ValidationError):
        OrderIn(user_id="user123")


def test_order_out_valid():
    """Test OrderOut with valid data."""
    order = OrderOut(
        order_id="order123",
        poll_url="http://poll.url",
        status="PENDING",
        requested_at="2024-01-01T00:00:00Z",
    )
    assert order.order_id == "order123"
    assert order.poll_url == "http://poll.url"
    assert order.status == "PENDING"
    assert order.requested_at == "2024-01-01T00:00:00Z"


def test_order_out_default_status():
    """Test OrderOut with default status."""
    order = OrderOut(
        order_id="order123",
        poll_url="http://poll.url",
        requested_at="2024-01-01T00:00:00Z",
    )
    assert order.status == "PENDING"


def test_token_valid():
    """Test Token with valid data."""
    token = Token(access_token="token123")
    assert token.access_token == "token123"
    assert token.token_type == "bearer"


def test_token_default_type():
    """Test Token with default token_type."""
    token = Token(access_token="token123")
    assert token.token_type == "bearer"


def test_token_custom_type():
    """Test Token with custom token_type."""
    token = Token(access_token="token123", token_type="bearer")
    assert token.token_type == "bearer"


def test_order_in_user_id_whitespace():
    """Test OrderIn with user_id containing only whitespace."""
    # This should pass validation (min_length=1), but may fail in practice
    order = OrderIn(user_id=" ", amount=1)
    assert order.user_id == " "


def test_order_in_amount_float():
    """Test OrderIn rejects float amounts."""
    with pytest.raises(ValidationError):
        OrderIn(user_id="user123", amount=100.5)


def test_order_in_amount_string_numeric():
    """Test OrderIn accepts numeric string amounts (Pydantic v2 coercion)."""
    # Pydantic v2 automatically coerces numeric strings to integers
    order = OrderIn(user_id="user123", amount="1000")
    assert order.amount == 1000
    assert isinstance(order.amount, int)


def test_order_in_amount_string():
    """Test OrderIn rejects non-numeric string amounts."""
    # Pydantic v2 coerces numeric strings to int, so test with non-numeric string
    with pytest.raises(ValidationError):
        OrderIn(user_id="user123", amount="abc")


def test_order_in_user_id_none():
    """Test OrderIn rejects None user_id."""
    with pytest.raises(ValidationError):
        OrderIn(user_id=None, amount=1000)


def test_order_in_amount_none():
    """Test OrderIn rejects None amount."""
    with pytest.raises(ValidationError):
        OrderIn(user_id="user123", amount=None)

