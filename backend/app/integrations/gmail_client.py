"""
Gmail API client integration.

This module handles direct communication with Gmail API:
1. Fetch emails (list + get message details)
2. Send emails (compose and send)
3. Delete emails (move to trash)
4. Parse Gmail's complex response format into clean objects

Gmail API Reference: https://developers.google.com/gmail/api/reference/rest
"""
import base64
import re
from email.mime.text import MIMEText
from typing import List, Optional, Tuple
from datetime import datetime

import httpx

from app.models.email import Email
from app.utils.logger import get_logger
from app.utils.errors import GmailError, EmailNotFoundError, RateLimitError, AuthError

logger = get_logger(__name__)

# Gmail API base URL
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


class GmailClient:
    """
    Gmail API client for email operations.
    
    Usage:
        client = GmailClient(access_token)
        emails = await client.fetch_emails(count=5)
        await client.send_email(to, subject, body)
        await client.delete_email(email_id)
    """
    
    def __init__(self, access_token: str):
        """
        Initialize Gmail client with access token.
        
        Args:
            access_token: Valid Google OAuth access token with Gmail scopes
        """
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: dict = None,
        params: dict = None,
        retries: int = 3,
    ) -> dict:
        """
        Make an authenticated request to Gmail API.
        
        Handles common error cases:
        - 401: Token expired/invalid
        - 403: Permission denied
        - 429: Rate limited
        - 5xx: Server errors
        
        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint (relative to base URL)
            json_data: Request body for POST
            params: Query parameters
            retries: Number of retries for transient errors
            
        Returns:
            Response JSON dict
            
        Raises:
            AuthError: Token issues
            GmailError: API errors
            RateLimitError: Rate limit exceeded
        """
        url = f"{GMAIL_API_BASE}{endpoint}"
        import asyncio
        
        for attempt in range(retries + 1):
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=self.headers,
                        json=json_data,
                        params=params,
                        timeout=30.0,
                    )
                    
                    # Handle success (including 204)
                    if 200 <= response.status_code < 300:
                        if response.status_code == 204 or not response.content:
                            return {}
                        return response.json()
                    
                    # Handle transient errors (Rate limit, Server error)
                    if response.status_code == 429 or response.status_code >= 500:
                        if attempt < retries:
                            wait_time = 2 ** attempt  # Exponential backoff
                            logger.warning(f"Gmail API transient error {response.status_code}, retrying in {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            continue
                    
                    # Handle 404
                    if response.status_code == 404:
                        return None
                    
                    # Handle Auth errors
                    if response.status_code == 401:
                        logger.warning("Gmail API: Token expired or invalid")
                        raise AuthError("Gmail access token expired")
                    
                    if response.status_code == 403:
                        logger.warning("Gmail API: Permission denied")
                        raise GmailError("Gmail permission denied. Please re-authorize.")
                    
                    # Handle other errors
                    error_data = response.json() if response.content else {}
                    logger.error(f"Gmail API error: {response.status_code} - {error_data}")
                    raise GmailError(f"Gmail API error: {response.status_code}")
                    
                except (httpx.TimeoutException, httpx.ConnectError) as e:
                    if attempt < retries:
                        wait_time = 2 ** attempt
                        logger.warning(f"Gmail API connection error, retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                        
                    logger.error(f"Gmail API: Request failed after {retries} retries - {e}")
                    raise GmailError("Gmail service unavailable. Please try again later.")
                    
                except (AuthError, GmailError):
                    raise
                except Exception as e:
                    logger.error(f"Unexpected Gmail API error: {e}")
                    raise GmailError(f"Unexpected error: {str(e)}")
    
    async def fetch_emails(self, count: int = 5, query: str = None) -> List[Email]:
        """
        Fetch the most recent emails from inbox.
        
        Gmail API flow:
        1. List message IDs (lightweight)
        2. Get full message details for each ID
        3. Parse into Email objects
        
        Args:
            count: Number of emails to fetch (default 5)
            query: Optional Gmail search query (e.g., "from:john", "subject:invoice")
            
        Returns:
            List of Email objects
        """
        logger.info(f"Fetching {count} emails (query: {query})")
        
        params = {
            "maxResults": count,
            "labelIds": "INBOX",
        }
        
        if query:
            params["q"] = query
        
        # Step 1: Get list of message IDs
        list_response = await self._make_request(
            "GET",
            "/messages",
            params=params
        )
        
        messages = list_response.get("messages", [])
        
        if not messages:
            logger.info("No emails found in inbox")
            return []
        
        # Step 2: Fetch full details for each message
        emails = []
        for msg in messages:
            try:
                email = await self._get_message_details(msg["id"])
                if email:
                    emails.append(email)
            except Exception as e:
                logger.warning(f"Failed to fetch email {msg['id']}: {e}")
                continue
        
        logger.info(f"Fetched {len(emails)} emails successfully")
        return emails
    
    async def _get_message_details(self, message_id: str) -> Optional[Email]:
        """
        Fetch full details for a single message.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            Email object or None
        """
        response = await self._make_request(
            "GET",
            f"/messages/{message_id}",
            params={"format": "full"}
        )
        
        if not response:
            return None
        
        return self._parse_message(response)
    
    def _parse_message(self, message: dict) -> Email:
        """
        Parse Gmail API message into Email object.
        
        Gmail message structure is complex. Headers are in a list,
        body may be nested in parts, and content is base64 encoded.
        
        Args:
            message: Raw Gmail API message response
            
        Returns:
            Clean Email object
        """
        # Extract headers
        headers = {h["name"].lower(): h["value"] for h in message.get("payload", {}).get("headers", [])}
        
        # Parse sender
        from_header = headers.get("from", "Unknown")
        sender_name, sender_email = self._parse_sender(from_header)
        
        # Parse date
        date_str = headers.get("date", "")
        internal_date = message.get("internalDate", "0")
        date = self._parse_date(date_str, internal_date)
        
        # Extract body
        body = self._extract_body(message.get("payload", {}))
        
        # Extract labels
        labels = message.get("labelIds", [])
        
        return Email(
            id=message["id"],
            thread_id=message.get("threadId", message["id"]),
            sender_name=sender_name,
            sender_email=sender_email,
            subject=headers.get("subject", "(No Subject)"),
            body=body,
            snippet=message.get("snippet", ""),
            date=date,
            labels=labels,
        )
    
    def _parse_sender(self, from_header: str) -> Tuple[str, str]:
        """
        Parse 'From' header into name and email.
        
        Handles formats:
        - "John Doe <john@example.com>"
        - "john@example.com"
        - "<john@example.com>"
        
        Returns:
            Tuple of (name, email)
        """
        # Try to match "Name <email>" format
        match = re.match(r'^"?([^"<]+)"?\s*<(.+)>$', from_header.strip())
        if match:
            return match.group(1).strip(), match.group(2).strip()
        
        # Try to match "<email>" format
        match = re.match(r'^<(.+)>$', from_header.strip())
        if match:
            email = match.group(1).strip()
            return email, email
        
        # Assume entire string is email
        email = from_header.strip()
        return email, email
    
    def _parse_date(self, date_str: str, internal_date: str) -> str:
        """
        Parse date into ISO format string.
        
        Uses internalDate (milliseconds since epoch) as fallback.
        
        Returns:
            ISO format date string
        """
        try:
            # Use internal date (more reliable)
            timestamp = int(internal_date) / 1000
            dt = datetime.fromtimestamp(timestamp)
            return dt.isoformat()
        except (ValueError, TypeError):
            pass
        
        # Return as-is if parsing fails
        return date_str or datetime.utcnow().isoformat()
    
    def _extract_body(self, payload: dict) -> str:
        """
        Extract email body from payload.
        
        Gmail stores body in various places:
        - Simple emails: payload.body.data
        - Multipart: payload.parts[*].body.data
        
        We prefer plain text over HTML.
        
        Returns:
            Decoded body text
        """
        # Try direct body
        if payload.get("body", {}).get("data"):
            return self._decode_body(payload["body"]["data"])
        
        # Try parts (multipart email)
        parts = payload.get("parts", [])
        
        # First, look for plain text
        for part in parts:
            if part.get("mimeType") == "text/plain":
                if part.get("body", {}).get("data"):
                    return self._decode_body(part["body"]["data"])
        
        # Fall back to HTML
        for part in parts:
            if part.get("mimeType") == "text/html":
                if part.get("body", {}).get("data"):
                    html = self._decode_body(part["body"]["data"])
                    return self._strip_html(html)
        
        # Check nested parts
        for part in parts:
            if "parts" in part:
                result = self._extract_body(part)
                if result:
                    return result
        
        return ""
    
    def _decode_body(self, data: str) -> str:
        """
        Decode base64url-encoded body data.
        
        Gmail uses URL-safe base64 encoding.
        """
        try:
            # Replace URL-safe characters
            data = data.replace("-", "+").replace("_", "/")
            # Add padding if needed
            padding = 4 - len(data) % 4
            if padding != 4:
                data += "=" * padding
            decoded = base64.b64decode(data)
            return decoded.decode("utf-8", errors="replace")
        except Exception as e:
            logger.warning(f"Failed to decode body: {e}")
            return ""
    
    def _strip_html(self, html: str) -> str:
        """
        Strip HTML tags to get plain text.
        
        Simple implementation - removes tags and decodes entities.
        """
        # Remove style and script blocks
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove HTML tags
        html = re.sub(r'<[^>]+>', ' ', html)
        
        # Decode common entities
        html = html.replace("&nbsp;", " ")
        html = html.replace("&amp;", "&")
        html = html.replace("&lt;", "<")
        html = html.replace("&gt;", ">")
        html = html.replace("&quot;", '"')
        
        # Clean up whitespace
        html = re.sub(r'\s+', ' ', html)
        
        return html.strip()
    
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        reply_to_id: Optional[str] = None,
    ) -> str:
        """
        Send an email.
        
        If reply_to_id is provided, sends as a reply to that message
        (includes In-Reply-To header and thread ID).
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Plain text body
            reply_to_id: Optional message ID to reply to
            
        Returns:
            Sent message ID
            
        Raises:
            GmailError: If send fails
        """
        logger.info(f"Sending email to: {to}")
        
        # Create message
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        
        # Get thread ID if this is a reply
        thread_id = None
        if reply_to_id:
            try:
                original = await self._make_request("GET", f"/messages/{reply_to_id}")
                if original:
                    thread_id = original.get("threadId")
                    # Get Message-ID header for In-Reply-To
                    headers = {h["name"].lower(): h["value"] for h in original.get("payload", {}).get("headers", [])}
                    if "message-id" in headers:
                        message["In-Reply-To"] = headers["message-id"]
                        message["References"] = headers["message-id"]
            except Exception as e:
                logger.warning(f"Failed to get original message for reply: {e}")
        
        # Encode message
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        
        # Build request body
        request_body = {"raw": raw}
        if thread_id:
            request_body["threadId"] = thread_id
        
        # Send
        response = await self._make_request(
            "POST",
            "/messages/send",
            json_data=request_body,
        )
        
        message_id = response.get("id", "unknown")
        logger.info(f"Email sent successfully, ID: {message_id}")
        
        return message_id
    
    async def delete_email(self, email_id: str) -> bool:
        """
        Delete an email (move to trash).
        
        We use trash instead of permanent delete for safety.
        User can recover from trash if needed.
        
        Args:
            email_id: Gmail message ID
            
        Returns:
            True if deleted
            
        Raises:
            EmailNotFoundError: If email doesn't exist
            GmailError: If delete fails
        """
        logger.info(f"Deleting email: {email_id}")
        
        response = await self._make_request(
            "POST",
            f"/messages/{email_id}/trash",
        )
        
        if response is None:
            raise EmailNotFoundError(email_id)
        
        logger.info(f"Email {email_id} moved to trash")
        return True
    
    async def get_email_by_id(self, email_id: str) -> Optional[Email]:
        """
        Get a specific email by ID.
        
        Args:
            email_id: Gmail message ID
            
        Returns:
            Email object or None if not found
        """
        return await self._get_message_details(email_id)
