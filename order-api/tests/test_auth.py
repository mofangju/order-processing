"""Tests for authentication endpoints."""

from datetime import datetime, timedelta, timezone

from app.auth import create_access_token
from fastapi.testclient import TestClient
from jose import jwt

from config import settings


def test_login_success(client: TestClient) -> None:
    """Test successful login returns a valid JWT token."""
    resp = client.post("/login", json={"user_id": "u123", "amount": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 0


def test_login_missing_fields(client: TestClient) -> None:
    """Test login with missing required fields returns validation error."""
    resp = client.post("/login", json={})
    assert resp.status_code == 422


def test_login_missing_user_id(client: TestClient) -> None:
    """Test login with missing user_id field."""
    resp = client.post("/login", json={"amount": 100})
    assert resp.status_code == 422


def test_login_missing_amount(client: TestClient) -> None:
    """Test login with missing amount field."""
    resp = client.post("/login", json={"user_id": "u123"})
    assert resp.status_code == 422


def test_login_invalid_user_id_empty(client: TestClient) -> None:
    """Test login with empty user_id."""
    resp = client.post("/login", json={"user_id": "", "amount": 1})
    assert resp.status_code == 422


def test_login_invalid_user_id_too_long(client: TestClient) -> None:
    """Test login with user_id exceeding max length."""
    long_user_id = "a" * 51  # Max is 50
    resp = client.post("/login", json={"user_id": long_user_id, "amount": 1})
    assert resp.status_code == 422


def test_login_invalid_amount_zero(client: TestClient) -> None:
    """Test login with amount of zero."""
    resp = client.post("/login", json={"user_id": "u123", "amount": 0})
    assert resp.status_code == 422


def test_login_invalid_amount_negative(client: TestClient) -> None:
    """Test login with negative amount."""
    resp = client.post("/login", json={"user_id": "u123", "amount": -1})
    assert resp.status_code == 422


def test_create_access_token() -> None:
    """Test token creation with different user IDs."""
    token1 = create_access_token("user1")
    token2 = create_access_token("user2")
    
    assert token1 != token2
    assert isinstance(token1, str)
    assert len(token1) > 0


def test_token_contains_user_id(client: TestClient) -> None:
    """Test that token can be decoded and contains user_id."""
    user_id = "test_user_123"
    resp = client.post("/login", json={"user_id": user_id, "amount": 1})
    assert resp.status_code == 200
    
    token = resp.json()["access_token"]
    payload = jwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
    assert payload["sub"] == user_id
    assert "exp" in payload


def test_token_expiration(client: TestClient) -> None:
    """Test that token has expiration claim."""
    resp = client.post("/login", json={"user_id": "u123", "amount": 1})
    token = resp.json()["access_token"]
    
    payload = jwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
    
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    now = datetime.now(timezone.utc)
    
    # Token should expire in approximately jwt_expires_minutes
    expected_exp = now + timedelta(minutes=settings.jwt_expires_minutes)
    # Allow 5 second tolerance
    assert abs((exp - expected_exp).total_seconds()) < 5


def test_token_expired(client: TestClient) -> None:
    """Test that expired token is rejected."""
    # Create an expired token
    expire = datetime.now(timezone.utc) - timedelta(minutes=1)
    to_encode = {"sub": "u123", "exp": expire}
    expired_token = jwt.encode(
        to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )
    
    # Try to use expired token
    resp = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {expired_token}"},
        json={"user_id": "u123", "amount": 999},
    )
    assert resp.status_code == 401


def test_token_wrong_secret(client: TestClient) -> None:
    """Test that token with wrong secret is rejected."""
    # Create token with wrong secret
    wrong_secret = "wrong-secret"
    to_encode = {"sub": "u123", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    wrong_token = jwt.encode(to_encode, wrong_secret, algorithm=settings.jwt_algorithm)
    
    resp = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {wrong_token}"},
        json={"user_id": "u123", "amount": 999},
    )
    assert resp.status_code == 401


def test_token_missing_sub(client: TestClient) -> None:
    """Test that token without subject claim is rejected."""
    # Create token without 'sub' claim
    to_encode = {"exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    token = jwt.encode(
        to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )
    
    resp = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": "u123", "amount": 999},
    )
    assert resp.status_code == 401
