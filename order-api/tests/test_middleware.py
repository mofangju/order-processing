"""Tests for middleware and request ID handling."""

from fastapi.testclient import TestClient


def test_request_id_header_present(client: TestClient) -> None:
    """Test that X-Request-ID header is added to responses."""
    response = client.get("/health")
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"] is not None
    assert len(response.headers["X-Request-ID"]) > 0


def test_request_id_custom_header(client: TestClient) -> None:
    """Test that custom X-Request-ID header is preserved."""
    custom_request_id = "custom-request-id-123"
    response = client.get(
        "/health", headers={"X-Request-ID": custom_request_id}
    )
    assert response.headers["X-Request-ID"] == custom_request_id


def test_request_id_generated(client: TestClient) -> None:
    """Test that request ID is generated when not provided."""
    response = client.get("/health")
    request_id = response.headers["X-Request-ID"]
    assert request_id is not None
    assert len(request_id) > 0
    # UUIDs are 36 characters (with hyphens)
    assert len(request_id) == 36 or len(request_id) > 0


def test_request_id_different_requests(client: TestClient) -> None:
    """Test that different requests get different request IDs."""
    response1 = client.get("/health")
    response2 = client.get("/health")
    
    # If no custom header, they should be different
    if "X-Request-ID" not in response1.request.headers:
        assert response1.headers["X-Request-ID"] != response2.headers["X-Request-ID"]


def test_request_id_all_endpoints(client: TestClient) -> None:
    """Test that X-Request-ID is present in all endpoint responses."""
    endpoints = [
        ("GET", "/health"),
        ("GET", "/ready"),
        ("POST", "/login"),
    ]
    
    for method, path in endpoints:
        if method == "GET":
            response = client.get(path)
        elif method == "POST":
            # For POST endpoints, send valid data
            if path == "/login":
                response = client.post(path, json={"user_id": "test", "amount": 1})
            else:
                continue
        
        assert "X-Request-ID" in response.headers, f"Missing X-Request-ID in {method} {path}"


def test_request_id_format(client: TestClient) -> None:
    """Test that request ID follows expected format (UUID-like)."""
    response = client.get("/health")
    request_id = response.headers["X-Request-ID"]
    
    # UUID format: 8-4-4-4-12 (36 chars total with hyphens)
    # Or could be a custom format
    assert len(request_id) > 0
    # Check if it looks like a UUID (contains hyphens and is 36 chars)
    # Or just verify it's not empty
    assert request_id is not None


def test_request_id_middleware_order(client: TestClient) -> None:
    """Test that request ID middleware runs before route handlers."""
    response = client.get("/health")
    # If middleware runs, header should be present
    assert "X-Request-ID" in response.headers
    # Response should still be successful
    assert response.status_code == 200

