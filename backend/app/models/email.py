"""
Email-related Pydantic models.
"""
from pydantic import BaseModel
from typing import Optional, List


class Email(BaseModel):
    """Full email data from Gmail."""
    id: str
    thread_id: str
    sender_name: str
    sender_email: str
    subject: str
    body: str
    snippet: str
    date: str
    labels: List[str] = []


class EmailReference(BaseModel):
    """Reference to an email (for deletion, reply, etc)."""
    type: str  # index, sender, subject
    value: str


class SendEmailRequest(BaseModel):
    """Request to send an email."""
    to: str
    subject: str
    body: str
    reply_to_id: Optional[str] = None
