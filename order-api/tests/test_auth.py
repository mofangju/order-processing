def test_login_success(client):
    resp = client.post(
        "/login",
        json={"user_id": "u123", "amount": 1}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_missing_fields(client):
    resp = client.post("/login", json={})
    assert resp.status_code == 422    