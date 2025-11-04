"""Tests for order creation endpoints."""

from app.auth import create_access_token
from fastapi.testclient import TestClient


def get_token(user_id: str = "u123") -> str:
    """Helper function to generate a test JWT token."""
    return create_access_token(user_id)


def test_create_order_success(client: TestClient, fake_handler: None) -> None:
    """Test successful order creation returns correct response."""
    token = get_token()
    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": "u123", "amount": 999},
    )
    assert response.status_code == 202
    data = response.json()
    assert "order_id" in data
    assert isinstance(data["order_id"], str)
    assert len(data["order_id"]) > 0
    assert "poll_url" in data
    assert isinstance(data["poll_url"], str)
    assert data["status"] == "PENDING"
    assert "requested_at" in data
    assert isinstance(data["requested_at"], str)


def test_create_order_unauthorized(client: TestClient) -> None:
    """Test order creation without authentication returns 403."""
    response = client.post("/orders", json={"user_id": "u123", "amount": 999})
    assert response.status_code == 403


def test_create_order_invalid_token(client: TestClient) -> None:
    """Test order creation with invalid token returns 401."""
    response = client.post(
        "/orders",
        headers={"Authorization": "Bearer invalid"},
        json={"user_id": "u123", "amount": 999},
    )
    assert response.status_code == 401


def test_create_order_malformed_token(client: TestClient) -> None:
    """Test order creation with malformed token."""
    response = client.post(
        "/orders",
        headers={"Authorization": "Bearer not.a.valid.token"},
        json={"user_id": "u123", "amount": 999},
    )
    assert response.status_code == 401


def test_create_order_missing_user_id(client: TestClient, fake_handler: None) -> None:
    """Test order creation with missing user_id field."""
    token = get_token()
    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"amount": 999},
    )
    assert response.status_code == 422


def test_create_order_missing_amount(client: TestClient, fake_handler: None) -> None:
    """Test order creation with missing amount field."""
    token = get_token()
    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": "u123"},
    )
    assert response.status_code == 422


def test_create_order_invalid_amount_zero(client: TestClient, fake_handler: None) -> None:
    """Test order creation with amount of zero."""
    token = get_token()
    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": "u123", "amount": 0},
    )
    assert response.status_code == 422


def test_create_order_invalid_amount_negative(client: TestClient, fake_handler: None) -> None:
    """Test order creation with negative amount."""
    token = get_token()
    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": "u123", "amount": -1},
    )
    assert response.status_code == 422


def test_create_order_invalid_user_id_empty(client: TestClient, fake_handler: None) -> None:
    """Test order creation with empty user_id."""
    token = get_token()
    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": "", "amount": 999},
    )
    assert response.status_code == 422


def test_create_order_invalid_user_id_too_long(client: TestClient, fake_handler: None) -> None:
    """Test order creation with user_id exceeding max length."""
    token = get_token()
    long_user_id = "a" * 51  # Max is 50
    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": long_user_id, "amount": 999},
    )
    assert response.status_code == 422


def test_create_order_minimum_amount(client: TestClient, fake_handler: None) -> None:
    """Test order creation with minimum valid amount (1 cent)."""
    token = get_token()
    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": "u123", "amount": 1},
    )
    assert response.status_code == 202
    data = response.json()
    assert "order_id" in data


def test_create_order_maximum_user_id_length(client: TestClient, fake_handler: None) -> None:
    """Test order creation with maximum valid user_id length."""
    token = get_token()
    max_user_id = "a" * 50  # Max is 50
    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": max_user_id, "amount": 999},
    )
    assert response.status_code == 202


def test_create_order_large_amount(client: TestClient, fake_handler: None) -> None:
    """Test order creation with large amount."""
    token = get_token()
    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": "u123", "amount": 999999999},
    )
    assert response.status_code == 202


def test_create_order_different_user_ids(client: TestClient, fake_handler: None) -> None:
    """Test order creation with different user IDs."""
    token1 = get_token("user1")
    token2 = get_token("user2")
    
    response1 = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token1}"},
        json={"user_id": "user1", "amount": 100},
    )
    response2 = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token2}"},
        json={"user_id": "user2", "amount": 200},
    )
    
    assert response1.status_code == 202
    assert response2.status_code == 202
    
    data1 = response1.json()
    data2 = response2.json()
    
    # Order IDs should be unique
    assert data1["order_id"] != data2["order_id"]


def test_create_order_wrong_authorization_format(client: TestClient) -> None:
    """Test order creation with wrong authorization header format."""
    response = client.post(
        "/orders",
        headers={"Authorization": "InvalidFormat token"},
        json={"user_id": "u123", "amount": 999},
    )
    assert response.status_code in [401, 403]


def test_create_order_missing_authorization_header(client: TestClient) -> None:
    """Test order creation without Authorization header."""
    response = client.post(
        "/orders",
        json={"user_id": "u123", "amount": 999},
    )
    assert response.status_code == 403


def test_create_order_empty_body(client: TestClient) -> None:
    """Test order creation with empty request body."""
    token = get_token()
    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )
    assert response.status_code == 422


def test_create_order_invalid_json(client: TestClient) -> None:
    """Test order creation with invalid JSON."""
    token = get_token()
    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        data="invalid json",
    )
    assert response.status_code == 422
