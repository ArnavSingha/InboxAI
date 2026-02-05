"""
User profile endpoint.
"""
from fastapi import APIRouter, Request, HTTPException, Depends

from app.services.session_service import SessionService, get_current_session
from app.models.user import UserResponse
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)
session_service = SessionService()


@router.get("/user", response_model=UserResponse)
async def get_user(session: dict = Depends(get_current_session)):
    """
    Get current user's profile information.
    """
    return UserResponse(
        email=session["email"],
        name=session["name"],
        picture=session.get("picture"),
    )
