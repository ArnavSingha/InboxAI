"""
Chat-related Pydantic models.
"""
from pydantic import BaseModel
from typing import Optional, List, Any


class ChatRequest(BaseModel):
    """Chat message request from frontend."""
    message: str


class EmailSummary(BaseModel):
    """Email summary for display in chat."""
    id: str
    index: int
    sender_name: str
    sender_email: str
    subject: str
    summary: str
    date: str


class CategoryGroup(BaseModel):
    """Grouped emails by category."""
    category: str
    emails: List[EmailSummary]
    count: int


class DigestSummary(BaseModel):
    """Daily digest summary."""
    summary: str
    key_emails: List[EmailSummary]
    suggested_actions: List[str]


class DraftReply(BaseModel):
    """Draft reply awaiting confirmation."""
    email_id: str
    to: str
    subject: str
    body: str


class ChatResponse(BaseModel):
    """Chat response to frontend."""
    message: str
    type: str = "text"  # text, emails, categories, digest, draft, confirmation, error
    data: Optional[Any] = None
    pending_action: Optional[str] = None  # send, delete
