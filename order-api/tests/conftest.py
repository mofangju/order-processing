from fastapi.testclient import TestClient
from app.main import app      
import pytest                 


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as client:
        yield client


@pytest.fixture
def fake_handler(monkeypatch):
    def handle_order(ddb, order_id, order_in, sqs, user_id):
        signed_url = "http://signed_url.com"
        return signed_url
    
    monkeypatch.setattr(
        "app.main.handle_order",
        handle_order
    )
