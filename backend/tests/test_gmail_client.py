"""
Unit tests for Gmail Client.

Tests Gmail response parsing and email creation with mocked HTTP.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import base64

from app.integrations.gmail_client import GmailClient, parse_email_message
from app.models.email import Email


class TestEmailParsing:
    """Test Gmail message parsing."""

    def test_parse_simple_message(self, mock_gmail_message):
        """Test parsing a simple text/plain message."""
        email = parse_email_message(mock_gmail_message, 1)
        
        assert email.id == "msg-abc123"
        assert email.thread_id == "thread-xyz789"
        assert email.sender_name == "John Doe"
        assert email.sender_email == "john@example.com"
        assert email.subject == "Test Subject"
        assert "email body" in email.body.lower()

    def test_parse_multipart_message(self, mock_gmail_multipart_message):
        """Test parsing a multipart message (prefers text/plain)."""
        email = parse_email_message(mock_gmail_multipart_message, 2)
        
        assert email.id == "msg-multi123"
        assert email.sender_name == "Jane Smith"
        assert email.sender_email == "jane@example.com"
        assert email.subject == "Multipart Email"
        # Should get plain text part, not HTML
        assert "Plain text body" in email.body

    def test_parse_sender_formats(self):
        """Test parsing different sender header formats."""
        # Format: "Name <email>"
        msg1 = {
            "id": "1",
            "threadId": "t1",
            "snippet": "test",
            "payload": {
                "headers": [
                    {"name": "From", "value": "John Doe <john@example.com>"},
                    {"name": "Subject", "value": "Test"},
                ],
                "body": {"data": "dGVzdA=="},  # "test"
            },
        }
        email1 = parse_email_message(msg1, 1)
        assert email1.sender_name == "John Doe"
        assert email1.sender_email == "john@example.com"

        # Format: just email
        msg2 = {
            "id": "2",
            "threadId": "t2",
            "snippet": "test",
            "payload": {
                "headers": [
                    {"name": "From", "value": "simple@example.com"},
                    {"name": "Subject", "value": "Test"},
                ],
                "body": {"data": "dGVzdA=="},
            },
        }
        email2 = parse_email_message(msg2, 2)
        assert email2.sender_email == "simple@example.com"

    def test_parse_missing_fields(self):
        """Test parsing message with missing optional fields."""
        minimal_msg = {
            "id": "min-123",
            "threadId": "thread-min",
            "snippet": "minimal message",
            "payload": {
                "headers": [],
                "body": {},
            },
        }
        email = parse_email_message(minimal_msg, 1)
        
        assert email.id == "min-123"
        assert email.snippet == "minimal message"
        assert email.sender_name == "Unknown"
        assert email.subject == "(No Subject)"

    def test_base64_decoding(self):
        """Test proper base64 decoding of email body."""
        test_content = "Hello, this is a test email with special chars: é, ñ, ü"
        encoded = base64.urlsafe_b64encode(test_content.encode()).decode()
        
        msg = {
            "id": "b64-test",
            "threadId": "thread-b64",
            "snippet": "snippet",
            "payload": {
                "headers": [
                    {"name": "From", "value": "test@example.com"},
                    {"name": "Subject", "value": "Test"},
                ],
                "mimeType": "text/plain",
                "body": {"data": encoded},
            },
        }
        email = parse_email_message(msg, 1)
        assert email.body == test_content


class TestGmailClientMethods:
    """Test GmailClient methods with mocked HTTP."""

    @pytest.fixture
    def gmail_client(self):
        """Create a GmailClient instance."""
        return GmailClient("mock-access-token")

    @pytest.mark.asyncio
    async def test_fetch_emails_success(self, gmail_client, mock_gmail_message):
        """Test successful email fetching."""
        # Mock the list and get API calls
        with patch.object(gmail_client, '_make_request', new_callable=AsyncMock) as mock_request:
            # First call: list messages
            mock_request.side_effect = [
                {"messages": [{"id": "msg-1"}, {"id": "msg-2"}]},  # list
                mock_gmail_message,  # get msg-1
                {**mock_gmail_message, "id": "msg-2"},  # get msg-2
            ]
            
            emails = await gmail_client.fetch_emails(count=2)
            
            assert len(emails) == 2
            assert mock_request.call_count == 3  # 1 list + 2 gets

    @pytest.mark.asyncio
    async def test_fetch_emails_empty_inbox(self, gmail_client):
        """Test fetching from empty inbox."""
        with patch.object(gmail_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"messages": []}
            
            emails = await gmail_client.fetch_emails()
            
            assert emails == []

    @pytest.mark.asyncio
    async def test_send_email_success(self, gmail_client):
        """Test successful email sending."""
        with patch.object(gmail_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"id": "sent-123"}
            
            message_id = await gmail_client.send_email(
                to="recipient@example.com",
                subject="Test Subject",
                body="Test body content",
            )
            
            assert message_id == "sent-123"
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_reply_includes_thread_id(self, gmail_client):
        """Test that reply emails include thread ID."""
        with patch.object(gmail_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"id": "sent-reply-123", "threadId": "thread-456"}
            
            message_id = await gmail_client.send_email(
                to="recipient@example.com",
                subject="Re: Original Subject",
                body="Reply content",
                reply_to_message_id="original-msg-id",
                thread_id="thread-456",
            )
            
            assert message_id == "sent-reply-123"
            # Verify thread_id was included in request
            call_args = mock_request.call_args
            assert "threadId" in str(call_args) or thread_id is not None

    @pytest.mark.asyncio
    async def test_delete_email_success(self, gmail_client):
        """Test successful email deletion (trash)."""
        with patch.object(gmail_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {}
            
            await gmail_client.delete_email("email-to-delete")
            
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            # Should use trash endpoint, not permanent delete
            assert "trash" in str(call_args).lower()


class TestGmailClientErrorHandling:
    """Test GmailClient error handling."""

    @pytest.fixture
    def gmail_client(self):
        """Create a GmailClient instance."""
        return GmailClient("mock-access-token")

    @pytest.mark.asyncio
    async def test_handles_401_error(self, gmail_client):
        """Test handling of 401 Unauthorized errors."""
        from app.utils.errors import AuthenticationError
        
        with patch.object(gmail_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = AuthenticationError("Token expired")
            
            with pytest.raises(AuthenticationError):
                await gmail_client.fetch_emails()

    @pytest.mark.asyncio
    async def test_handles_rate_limit_error(self, gmail_client):
        """Test handling of 429 rate limit errors."""
        from app.utils.errors import RateLimitError
        
        with patch.object(gmail_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = RateLimitError("Too many requests")
            
            with pytest.raises(RateLimitError):
                await gmail_client.fetch_emails()


class TestEmailModel:
    """Test Email Pydantic model."""

    def test_email_model_creation(self):
        """Test creating an Email model."""
        email = Email(
            id="test-id",
            thread_id="thread-id",
            sender_name="Test Sender",
            sender_email="sender@example.com",
            subject="Test Subject",
            snippet="Test snippet...",
            body="Full body content",
            date="2025-02-05T10:00:00Z",
        )
        
        assert email.id == "test-id"
        assert email.sender_name == "Test Sender"
        assert email.subject == "Test Subject"

    def test_email_model_to_dict(self):
        """Test Email model serialization."""
        email = Email(
            id="test-id",
            thread_id="thread-id",
            sender_name="Test Sender",
            sender_email="sender@example.com",
            subject="Test Subject",
            snippet="Test snippet...",
            body="Full body content",
            date="2025-02-05T10:00:00Z",
        )
        
        data = email.model_dump()
        
        assert isinstance(data, dict)
        assert data["id"] == "test-id"
        assert data["subject"] == "Test Subject"
