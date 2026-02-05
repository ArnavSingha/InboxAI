"""
Session-related Pydantic models.
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class Session(BaseModel):
    """User session data."""
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    access_token: str
    refresh_token: str
    token_expiry: datetime
    created_at: datetime
    
    # Session state for pending actions
    emails_cache: List[dict] = []
    pending_action: Optional[str] = None  # send, delete
    pending_data: Optional[dict] = None
