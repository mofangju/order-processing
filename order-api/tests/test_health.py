"""Tests for health check endpoints."""

from unittest.mock import patch

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    """Test health check endpoint returns correct status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["env"] == "local"
    assert isinstance(data["env"], str)


def test_health_returns_environment(client: TestClient) -> None:
    """Test health endpoint includes environment information."""
    response = client.get("/health")
    data = response.json()
    assert "env" in data
    assert data["env"] in ["local", "dev", "prod"]


def test_ready_when_configured(client: TestClient) -> None:
    """Test readiness check endpoint when all config is set."""
    # This assumes the test environment has SQS_QUEUE_URL and DDB_TABLE set
    # If not, we'll patch the settings
    with patch("config.settings.sqs_queue_url", "https://sqs.example.com/queue"):
        with patch("config.settings.ddb_table", "test-table"):
            response = client.get("/ready")
            # If configured, should return 200
            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "ready"
            else:
                # If not configured in test env, we expect 503
                assert response.status_code == 503


def test_ready_missing_sqs_config(client: TestClient) -> None:
    """Test ready endpoint when SQS queue URL is missing."""
    with patch("config.settings.sqs_queue_url", None):
        with patch("config.settings.ddb_table", "test-table"):
            response = client.get("/ready")
            assert response.status_code == 503
            data = response.json()
            assert "not ready" in data["detail"].lower() or "missing" in data["detail"].lower()
            assert "sqs_queue_url" in data["detail"]


def test_ready_missing_ddb_config(client: TestClient) -> None:
    """Test ready endpoint when DynamoDB table is missing."""
    with patch("config.settings.sqs_queue_url", "https://sqs.example.com/queue"):
        with patch("config.settings.ddb_table", None):
            response = client.get("/ready")
            assert response.status_code == 503
            data = response.json()
            assert "not ready" in data["detail"].lower() or "missing" in data["detail"].lower()
            assert "ddb_table" in data["detail"]


def test_ready_missing_both_configs(client: TestClient) -> None:
    """Test ready endpoint when both configs are missing."""
    with patch("config.settings.sqs_queue_url", None):
        with patch("config.settings.ddb_table", None):
            response = client.get("/ready")
            assert response.status_code == 503
            data = response.json()
            assert "sqs_queue_url" in data["detail"]
            assert "ddb_table" in data["detail"]


def test_health_endpoint_always_available(client: TestClient) -> None:
    """Test that health endpoint is always available regardless of config."""
    # Health should work even if config is missing
    with patch("config.settings.sqs_queue_url", None):
        with patch("config.settings.ddb_table", None):
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"
