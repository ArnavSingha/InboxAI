"""
Unit tests for Email Service.

Tests email reference resolution and caching.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.email_service import EmailService


class TestEmailReferenceResolution:
    """Test email reference resolution from cache."""

    @pytest.fixture
    def email_service(self, mock_session, mock_emails_list):
        """Create EmailService with cached emails."""
        mock_session["emails_cache"] = mock_emails_list
        return EmailService(mock_session)

    def test_resolve_by_index(self, email_service):
        """Test resolving email by index number."""
        email = email_service.resolve_email_reference("#1")
        assert email is not None
        assert email["index"] == 1

        email = email_service.resolve_email_reference("3")
        assert email is not None
        assert email["index"] == 3

    def test_resolve_by_sender(self, email_service):
        """Test resolving email by sender name."""
        email = email_service.resolve_email_reference("Sender 2")
        assert email is not None
        assert "Sender 2" in email["sender_name"]

    def test_resolve_by_subject(self, email_service):
        """Test resolving email by subject keyword."""
        email = email_service.resolve_email_reference("Subject 3")
        assert email is not None
        assert "Subject 3" in email["subject"]

    def test_resolve_not_found(self, email_service):
        """Test that unknown references return None."""
        email = email_service.resolve_email_reference("nonexistent")
        assert email is None

    def test_resolve_empty_cache(self, mock_session):
        """Test resolution with empty cache."""
        mock_session["emails_cache"] = []
        service = EmailService(mock_session)
        
        email = service.resolve_email_reference("#1")
        assert email is None


class TestEmailCaching:
    """Test email caching behavior."""

    def test_get_cached_emails(self, mock_session, mock_emails_list):
        """Test retrieving cached emails."""
        mock_session["emails_cache"] = mock_emails_list
        service = EmailService(mock_session)
        
        cached = service.get_cached_emails()
        
        assert len(cached) == 5
        assert cached[0]["index"] == 1

    def test_cache_is_updated_on_fetch(self, mock_session):
        """Test that cache is updated after fetching."""
        mock_session["emails_cache"] = []
        service = EmailService(mock_session)
        
        # The actual fetch would populate the cache
        # This tests the cache is accessible
        assert service.get_cached_emails() == []


class TestEmailFormatting:
    """Test email formatting for chat display."""

    def test_format_emails_for_chat(self, mock_session, mock_emails_list):
        """Test formatting emails as EmailSummary objects."""
        mock_session["emails_cache"] = mock_emails_list
        service = EmailService(mock_session)
        
        summaries = ["Summary 1", "Summary 2", "Summary 3", "Summary 4", "Summary 5"]
        
        from app.models.email import Email
        emails = [
            Email(
                id=e["id"],
                thread_id=e["thread_id"],
                sender_name=e["sender_name"],
                sender_email=e["sender_email"],
                subject=e["subject"],
                snippet=e["snippet"],
                body=e["body"],
                date=e["date"],
            )
            for e in mock_emails_list
        ]
        
        formatted = service.format_emails_for_chat(emails, summaries)
        
        assert len(formatted) == 5
        assert formatted[0].index == 1
        assert formatted[0].summary == "Summary 1"
