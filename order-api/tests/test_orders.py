from app.auth import create_access_token


def get_token(user_id: str = "u123"):
    token = create_access_token(user_id)
    return token


def test_create_order_success(client, fake_handler):
    token = get_token()
    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": "u123", "amount": 999},
    )
    assert response.status_code == 202
    data = response.json()
    assert data["order_id"]
    assert "poll_url" in data
    assert data["status"] == "PENDING"
    assert "requested_at" in data


def test_create_order_unauthorized(client):
    response = client.post("/orders", json={"user_id": "u123", "amount": 999})
    assert response.status_code == 403


def test_create_order_invalid_token(client):
    response = client.post(
        "/orders",
        headers={"Authorization": "Bearer invalid"},
        json={"user_id": "u123", "amount": 999},
    )
    assert response.status_code == 401
