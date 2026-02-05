"""
Pytest fixtures for InboxAI backend tests.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_session():
    """Create a mock user session."""
    return {
        "session_id": "test-session-123",
        "email": "test@example.com",
        "name": "Test User",
        "picture": "https://example.com/avatar.jpg",
        "access_token": "mock-access-token",
        "refresh_token": "mock-refresh-token",
        "token_expires_at": 9999999999,
        "pending_action": None,
        "pending_data": None,
        "emails_cache": [],
    }


@pytest.fixture
def mock_email():
    """Create a mock email for testing."""
    return {
        "id": "email-123",
        "thread_id": "thread-456",
        "sender_name": "John Doe",
        "sender_email": "john@example.com",
        "subject": "Test Email Subject",
        "snippet": "This is a preview of the email content...",
        "body": "This is the full body of the test email.",
        "date": "2025-02-05T10:30:00Z",
        "index": 1,
    }


@pytest.fixture
def mock_emails_list():
    """Create a list of mock emails."""
    return [
        {
            "id": f"email-{i}",
            "thread_id": f"thread-{i}",
            "sender_name": f"Sender {i}",
            "sender_email": f"sender{i}@example.com",
            "subject": f"Test Subject {i}",
            "snippet": f"Preview of email {i}...",
            "body": f"Body of email {i}",
            "date": f"2025-02-0{i}T10:00:00Z",
            "index": i,
        }
        for i in range(1, 6)
    ]


@pytest.fixture
def mock_gmail_message():
    """Create a mock Gmail API message response."""
    return {
        "id": "msg-abc123",
        "threadId": "thread-xyz789",
        "labelIds": ["INBOX", "UNREAD"],
        "snippet": "This is the email snippet...",
        "payload": {
            "headers": [
                {"name": "From", "value": "John Doe <john@example.com>"},
                {"name": "To", "value": "me@example.com"},
                {"name": "Subject", "value": "Test Subject"},
                {"name": "Date", "value": "Wed, 5 Feb 2025 10:30:00 +0000"},
            ],
            "mimeType": "text/plain",
            "body": {
                "data": "VGhpcyBpcyB0aGUgZW1haWwgYm9keQ=="  # Base64 "This is the email body"
            },
        },
    }


@pytest.fixture
def mock_gmail_multipart_message():
    """Create a mock Gmail API multipart message."""
    return {
        "id": "msg-multi123",
        "threadId": "thread-multi789",
        "labelIds": ["INBOX"],
        "snippet": "Multipart email snippet...",
        "payload": {
            "headers": [
                {"name": "From", "value": "Jane Smith <jane@example.com>"},
                {"name": "Subject", "value": "Multipart Email"},
                {"name": "Date", "value": "Wed, 5 Feb 2025 11:00:00 +0000"},
            ],
            "mimeType": "multipart/alternative",
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {
                        "data": "UGxhaW4gdGV4dCBib2R5"  # "Plain text body"
                    },
                },
                {
                    "mimeType": "text/html",
                    "body": {
                        "data": "PHA+SFRNTCBib2R5PC9wPg=="  # "<p>HTML body</p>"
                    },
                },
            ],
        },
    }


@pytest.fixture
def mock_openai_response():
    """Create a mock OpenAI API response."""
    return MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content='{"intent": "READ_EMAILS", "confidence": 0.95, "params": {}}'
                )
            )
        ],
        usage=MagicMock(total_tokens=50),
    )
