import jwt

SECRET = "test-secret"
ALGO = "HS256"

def get_token(user_id: str = "u123"):
    return jwt.encode({"sub": user_id, "exp": 9999999999}, SECRET, algorithm=ALGO)

def test_create_order_success(client):
    token = get_token()
    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": "u123", "amount": 999}
    )
    assert response.status_code == 202
    data = response.json()
    assert data["order_id"]
    assert "poll_url" in data
    assert data["status"] == "PENDING"
    assert "requested_at" in data

def test_create_order_unauthorized(client):
    response = client.post("/orders", json={"user_id": "u123", "amount": 999})
    assert response.status_code == 401

def test_create_order_invalid_token(client):
    response = client.post(
        "/orders",
        headers={"Authorization": "Bearer invalid"},
        json={"user_id": "u123", "amount": 999}
    )
    assert response.status_code == 401

def test_rate_limit(client):
    token = get_token()
    # First 5 should pass
    for _ in range(5):
        resp = client.post(
            "/orders",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": "u123", "amount": 100}
        )
        assert resp.status_code == 202

    # 6th should fail
    resp = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": "u123", "amount": 100}
    )
    assert resp.status_code == 429
    assert "rate limit" in resp.text.lower()