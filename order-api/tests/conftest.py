"""Pytest configuration and shared fixtures."""

import os
from typing import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI application."""
    # Ensure required settings are set for tests
    with patch.dict(
        os.environ,
        {
            "SQS_QUEUE_URL": "https://sqs.example.com/test-queue",
            "DDB_TABLE": "test-table",
        },
        clear=False,
    ):
        with TestClient(app) as test_client:
            yield test_client


@pytest.fixture
def fake_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock the handle_order function to avoid actual AWS calls."""
    def handle_order_mock(
        ddb,  # noqa: ANN001
        order_id: str,
        order_in,  # noqa: ANN001
        sqs,  # noqa: ANN001
        user_id: str,
    ) -> str:
        """Mock handler that returns a fake signed URL."""
        return "http://signed_url.com"

    monkeypatch.setattr("app.main.handle_order", handle_order_mock)


@pytest.fixture
def mock_aws_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock AWS settings for testing."""
    monkeypatch.setenv("SQS_QUEUE_URL", "https://sqs.example.com/test-queue")
    monkeypatch.setenv("DDB_TABLE", "test-table")
    monkeypatch.setenv("AWS_ENDPOINT_URL", "http://localhost:4566")  # LocalStack default
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
