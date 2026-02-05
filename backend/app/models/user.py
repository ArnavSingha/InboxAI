"""
User-related Pydantic models.
"""
from pydantic import BaseModel
from typing import Optional


class UserResponse(BaseModel):
    """User profile response."""
    email: str
    name: str
    picture: Optional[str] = None
