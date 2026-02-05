"""
Email service - business logic layer for email operations.

This module provides:
1. High-level email operations for the chat service
2. Email caching in session for reference resolution
3. Formatted responses for chat display
4. Error handling with user-friendly messages

The service sits between chat_service and gmail_client,
translating user intents into Gmail operations.
"""
from typing import List, Optional, Tuple

from app.integrations.gmail_client import GmailClient
from app.models.email import Email
from app.models.chat import EmailSummary
from app.services.session_service import update_session, get_session_id
from app.utils.logger import get_logger
from app.utils.errors import EmailNotFoundError, GmailError

logger = get_logger(__name__)


class EmailService:
    """
    Email service for chat-integrated email operations.
    
    Usage:
        service = EmailService(session)
        emails = await service.fetch_emails(count=5)
        await service.send_reply(email_id, body)
        await service.delete_email(email_id)
    """
    
    def __init__(self, session: dict, session_token: str = None):
        """
        Initialize email service with user session.
        
        Args:
            session: User session dict with tokens and cache
            session_token: Optional JWT for session updates
        """
        self.session = session
        self.session_token = session_token
        self.gmail = GmailClient(session["access_token"])
        
    async def fetch_emails(self, count: int = 5, query: str = None) -> List[Email]:
        """
        Fetch recent emails and cache them for reference.
        
        Caches emails in session so user can reference them
        by index (e.g., "reply to #2", "delete #3").
        
        Args:
            count: Number of emails to fetch
            query: Optional search query
            
        Returns:
            List of Email objects
        """
        emails = await self.gmail.fetch_emails(count=count, query=query)
        
        # Cache in session for reference resolution
        self._cache_emails(emails)
        
        logger.info(f"Fetched and cached {len(emails)} emails")
        return emails
    
    def _cache_emails(self, emails: List[Email]):
        """
        Cache emails in session for reference resolution.
        
        Converts Email objects to dicts for storage.
        """
        cache = []
        for i, email in enumerate(emails):
            cache.append({
                "index": i + 1,  # 1-indexed for user
                "id": email.id,
                "sender_name": email.sender_name,
                "sender_email": email.sender_email,
                "subject": email.subject,
                "body": email.body,
                "snippet": email.snippet,
                "date": email.date,
            })
        
        self.session["emails_cache"] = cache
    
    def get_cached_emails(self) -> List[dict]:
        """Get cached emails from session."""
        return self.session.get("emails_cache", [])
    
    def resolve_email_reference(self, reference: str) -> Optional[dict]:
        """
        Resolve a user's email reference to a cached email.
        
        Supports:
        - Index: "#1", "1", "email 1", "first", "second"
        - Sender name: "from John", "the LinkedIn one"
        - Subject keyword: "about meeting", "the invoice email"
        
        Args:
            reference: User's reference string
            
        Returns:
            Cached email dict or None
        """
        cache = self.get_cached_emails()
        
        if not cache:
            return None
        
        reference = reference.lower().strip()
        
        # Try index reference first
        email = self._resolve_index(reference, cache)
        if email:
            return email
        
        # Try sender reference
        email = self._resolve_sender(reference, cache)
        if email:
            return email
        
        # Try subject reference
        email = self._resolve_subject(reference, cache)
        if email:
            return email
        
        return None
    
    def _resolve_index(self, reference: str, cache: List[dict]) -> Optional[dict]:
        """
        Resolve index-based reference.
        
        Handles: "#1", "1", "email 1", "first", "second", etc.
        """
        # Ordinal words
        ordinals = {
            "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
            "1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5,
            "last": len(cache), "latest": 1, "most recent": 1,
        }
        
        for word, idx in ordinals.items():
            if word in reference:
                if 1 <= idx <= len(cache):
                    return cache[idx - 1]
        
        # Pattern matching for numbers
        import re
        patterns = [
            r'#(\d+)',           # #1, #2
            r'email\s*(\d+)',    # email 1, email2
            r'number\s*(\d+)',   # number 1
            r'^(\d+)$',          # just "1"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, reference)
            if match:
                idx = int(match.group(1))
                if 1 <= idx <= len(cache):
                    return cache[idx - 1]
        
        return None
    
    def _resolve_sender(self, reference: str, cache: List[dict]) -> Optional[dict]:
        """
        Resolve sender-based reference.
        
        Handles: "from John", "the one from LinkedIn", "John's email"
        """
        import re
        
        # Extract sender name from reference
        patterns = [
            r'from\s+(\w+)',        # from John
            r'(\w+)\'s\s+email',    # John's email
            r'the\s+(\w+)\s+one',   # the LinkedIn one
            r'the\s+(\w+)\s+email', # the LinkedIn email
        ]
        
        for pattern in patterns:
            match = re.search(pattern, reference, re.IGNORECASE)
            if match:
                sender_search = match.group(1).lower()
                
                # Find matching email
                for email in cache:
                    if sender_search in email["sender_name"].lower():
                        return email
                    if sender_search in email["sender_email"].lower():
                        return email
        
        # General search in sender fields
        for email in cache:
            sender_combined = f"{email['sender_name']} {email['sender_email']}".lower()
            # Check if any significant word from reference is in sender
            words = reference.replace("from", "").replace("email", "").split()
            for word in words:
                if len(word) > 2 and word in sender_combined:
                    return email
        
        return None
    
    def _resolve_subject(self, reference: str, cache: List[dict]) -> Optional[dict]:
        """
        Resolve subject-based reference.
        
        Handles: "about meeting", "the invoice email", "regarding project"
        """
        import re
        
        # Extract topic from reference
        patterns = [
            r'about\s+(.+)',     # about meeting
            r'regarding\s+(.+)', # regarding project
            r're:\s*(.+)',       # re: something
        ]
        
        for pattern in patterns:
            match = re.search(pattern, reference, re.IGNORECASE)
            if match:
                topic = match.group(1).lower().strip()
                
                for email in cache:
                    if topic in email["subject"].lower():
                        return email
        
        # Fallback: check if any words match subject
        words = reference.split()
        for email in cache:
            subject_lower = email["subject"].lower()
            for word in words:
                if len(word) > 3 and word in subject_lower:
                    return email
        
        return None
    
    async def send_reply(
        self,
        email_id: str,
        body: str,
        original_email: dict = None,
    ) -> str:
        """
        Send a reply to an email.
        
        Args:
            email_id: Original email ID to reply to
            body: Reply body text
            original_email: Optional cached email dict (for recipient)
            
        Returns:
            Sent message ID
        """
        # Get original email info if not provided
        if not original_email:
            original_email = await self.gmail.get_email_by_id(email_id)
            if not original_email:
                raise EmailNotFoundError(email_id)
            to = original_email.sender_email
            subject = f"Re: {original_email.subject}"
        else:
            to = original_email["sender_email"]
            subject = f"Re: {original_email['subject']}"
        
        message_id = await self.gmail.send_email(
            to=to,
            subject=subject,
            body=body,
            reply_to_id=email_id,
        )
        
        logger.info(f"Sent reply to {to}")
        return message_id
    
    async def delete_email(self, email_id: str) -> bool:
        """
        Delete an email (move to trash).
        
        Args:
            email_id: Email ID to delete
            
        Returns:
            True if successful
        """
        result = await self.gmail.delete_email(email_id)
        
        # Remove from cache
        cache = self.get_cached_emails()
        self.session["emails_cache"] = [e for e in cache if e["id"] != email_id]
        
        return result
    
    def format_emails_for_chat(
        self,
        emails: List[Email],
        summaries: List[str] = None,
    ) -> List[EmailSummary]:
        """
        Format emails for chat display.
        
        Args:
            emails: List of Email objects
            summaries: Optional AI-generated summaries
            
        Returns:
            List of EmailSummary for frontend
        """
        result = []
        for i, email in enumerate(emails):
            summary = summaries[i] if summaries and i < len(summaries) else email.snippet[:100]
            
            result.append(EmailSummary(
                id=email.id,
                index=i + 1,
                sender_name=email.sender_name,
                sender_email=email.sender_email,
                subject=email.subject,
                summary=summary,
                date=email.date,
            ))
        
        return result
    
    def get_email_for_confirmation(self, email: dict) -> str:
        """
        Format email for confirmation display.
        
        Returns a brief description for delete/reply confirmation.
        """
        return f"From: {email['sender_name']} <{email['sender_email']}>\nSubject: {email['subject']}"
