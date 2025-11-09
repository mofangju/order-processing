"""Tests for order handler business logic."""

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import BotoCoreError, ClientError

from app.handler import handle_order
from app.schemas import OrderIn


@pytest.fixture
def mock_sqs_client():
    """Create a mock SQS client."""
    client = MagicMock()
    return client


@pytest.fixture
def mock_ddb_client():
    """Create a mock DynamoDB client."""
    client = MagicMock()
    client.generate_presigned_url.return_value = "http://signed-url.com"
    return client


@pytest.fixture
def order_in():
    """Create a sample order input."""
    return OrderIn(user_id="test_user", amount=1000)


def test_handle_order_success(mock_sqs_client, mock_ddb_client, order_in):
    """Test successful order handling."""
    with patch("app.handler.settings.sqs_queue_url", "https://sqs.example.com/queue"):
        with patch("app.handler.settings.ddb_table", "test-table"):
            signed_url = handle_order(
                mock_ddb_client, "order123", order_in, mock_sqs_client, "user123"
            )
            
            assert signed_url == "http://signed-url.com"
            mock_sqs_client.send_message.assert_called_once()
            mock_ddb_client.generate_presigned_url.assert_called_once()


def test_handle_order_missing_sqs_url(mock_sqs_client, mock_ddb_client, order_in):
    """Test handler fails when SQS queue URL is missing."""
    with patch("app.handler.settings.sqs_queue_url", None):
        with pytest.raises(Exception) as exc_info:
            handle_order(
                mock_ddb_client, "order123", order_in, mock_sqs_client, "user123"
            )
        assert "not configured" in str(exc_info.value).lower() or exc_info.value.status_code == 503


def test_handle_order_missing_ddb_table(mock_sqs_client, mock_ddb_client, order_in):
    """Test handler fails when DynamoDB table is missing."""
    with patch("app.handler.settings.sqs_queue_url", "https://sqs.example.com/queue"):
        with patch("app.handler.settings.ddb_table", None):
            with pytest.raises(Exception) as exc_info:
                handle_order(
                    mock_ddb_client, "order123", order_in, mock_sqs_client, "user123"
                )
            assert "not configured" in str(exc_info.value).lower() or exc_info.value.status_code == 503


def test_handle_order_sqs_error(mock_sqs_client, mock_ddb_client, order_in):
    """Test handler handles SQS errors."""
    with patch("app.handler.settings.sqs_queue_url", "https://sqs.example.com/queue"):
        with patch("app.handler.settings.ddb_table", "test-table"):
            mock_sqs_client.send_message.side_effect = ClientError(
                {"Error": {"Code": "ServiceUnavailable"}}, "SendMessage"
            )
            
            with pytest.raises(Exception) as exc_info:
                handle_order(
                    mock_ddb_client, "order123", order_in, mock_sqs_client, "user123"
                )
            assert exc_info.value.status_code == 502


def test_handle_order_ddb_error(mock_sqs_client, mock_ddb_client, order_in):
    """Test handler handles DynamoDB errors."""
    with patch("app.handler.settings.sqs_queue_url", "https://sqs.example.com/queue"):
        with patch("app.handler.settings.ddb_table", "test-table"):
            mock_ddb_client.generate_presigned_url.side_effect = ClientError(
                {"Error": {"Code": "ResourceNotFoundException"}}, "GetItem"
            )
            
            with pytest.raises(Exception) as exc_info:
                handle_order(
                    mock_ddb_client, "order123", order_in, mock_sqs_client, "user123"
                )
            assert exc_info.value.status_code == 502


def test_handle_order_sqs_boto_error(mock_sqs_client, mock_ddb_client, order_in):
    """Test handler handles BotoCoreError from SQS."""
    with patch("app.handler.settings.sqs_queue_url", "https://sqs.example.com/queue"):
        with patch("app.handler.settings.ddb_table", "test-table"):
            mock_sqs_client.send_message.side_effect = BotoCoreError()
            
            with pytest.raises(Exception) as exc_info:
                handle_order(
                    mock_ddb_client, "order123", order_in, mock_sqs_client, "user123"
                )
            assert exc_info.value.status_code == 502


def test_handle_order_sqs_message_format(mock_sqs_client, mock_ddb_client, order_in):
    """Test that SQS message is formatted correctly."""
    with patch("app.handler.settings.sqs_queue_url", "https://sqs.example.com/queue"):
        with patch("app.handler.settings.ddb_table", "test-table"):
            handle_order(
                mock_ddb_client, "order123", order_in, mock_sqs_client, "user123"
            )
            
            call_args = mock_sqs_client.send_message.call_args
            assert call_args[1]["QueueUrl"] == "https://sqs.example.com/queue"
            assert call_args[1]["MessageGroupId"] == "user123"
            assert call_args[1]["MessageDeduplicationId"] == "order123"
            
            import json
            message_body = json.loads(call_args[1]["MessageBody"])
            assert message_body["order_id"] == "order123"
            assert message_body["user_id"] == "user123"
            assert message_body["amount"] == 1000


def test_handle_order_ddb_url_params(mock_sqs_client, mock_ddb_client, order_in):
    """Test that DynamoDB presigned URL parameters are correct."""
    with patch("app.handler.settings.sqs_queue_url", "https://sqs.example.com/queue"):
        with patch("app.handler.settings.ddb_table", "test-table"):
            handle_order(
                mock_ddb_client, "order123", order_in, mock_sqs_client, "user123"
            )
            
            call_args = mock_ddb_client.generate_presigned_url.call_args
            assert call_args[1]["ClientMethod"] == "get_item"
            assert call_args[1]["Params"]["TableName"] == "test-table"
            assert call_args[1]["Params"]["Key"]["order_id"]["S"] == "order123"
            assert call_args[1]["ExpiresIn"] == 300
            assert call_args[1]["HttpMethod"] == "GET"

