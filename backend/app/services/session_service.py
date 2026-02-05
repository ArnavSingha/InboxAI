"""
Session management service.

This module handles:
1. Creating and storing user sessions with tokens
2. Validating session cookies (JWT-based)
3. Retrieving session data for authenticated requests
4. Refreshing tokens when needed

Security: Sessions are stored in-memory (suitable for demo).
In production, use Redis or a database.
"""
import jwt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Request, HTTPException

from app.config import get_settings
from app.utils.logger import get_logger
from app.utils.errors import SessionExpiredError, AuthError

logger = get_logger(__name__)
settings = get_settings()

# In-memory session store
# Key: session_id (from JWT), Value: session data dict
_sessions: dict[str, dict] = {}


def create_session(
    user_id: str,
    email: str,
    name: str,
    picture: Optional[str],
    access_token: str,
    refresh_token: str,
    expires_in: int,
) -> str:
    """
    Create a new user session and return a JWT session token.
    
    The JWT contains only the session ID. Actual session data
    (tokens, user info) is stored server-side for security.
    
    Args:
        user_id: Google user ID
        email: User's email
        name: User's display name
        picture: User's profile picture URL
        access_token: Google access token
        refresh_token: Google refresh token
        expires_in: Token expiry in seconds
        
    Returns:
        JWT session token (to be stored in cookie)
    """
    session_id = f"{user_id}_{datetime.utcnow().timestamp()}"
    token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
    session_expiry = datetime.utcnow() + timedelta(hours=settings.session_expire_hours)
    
    # Store session data server-side
    _sessions[session_id] = {
        "user_id": user_id,
        "email": email,
        "name": name,
        "picture": picture,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_expiry": token_expiry,
        "session_expiry": session_expiry,
        "created_at": datetime.utcnow(),
        # For email operations - cache of fetched emails
        "emails_cache": [],
        # For pending confirmations
        "pending_action": None,
        "pending_data": None,
    }
    
    # Create JWT with session ID only
    jwt_payload = {
        "session_id": session_id,
        "exp": session_expiry,
        "iat": datetime.utcnow(),
    }
    
    token = jwt.encode(jwt_payload, settings.session_secret, algorithm="HS256")
    logger.info(f"Created session for user: {email}")
    
    return token


def get_session(session_token: str) -> Optional[dict]:
    """
    Retrieve session data from a JWT session token.
    
    Validates the JWT and returns the associated session data.
    Returns None if JWT is invalid or session doesn't exist.
    
    Args:
        session_token: JWT from session cookie
        
    Returns:
        Session data dict or None
    """
    try:
        payload = jwt.decode(
            session_token,
            settings.session_secret,
            algorithms=["HS256"]
        )
        
        session_id = payload.get("session_id")
        if not session_id or session_id not in _sessions:
            logger.warning("Session not found in store")
            return None
        
        session = _sessions[session_id]
        
        # Check if session is expired
        if datetime.utcnow() > session["session_expiry"]:
            logger.info(f"Session expired for: {session['email']}")
            delete_session(session_token)
            return None
        
        return session
        
    except jwt.ExpiredSignatureError:
        logger.warning("JWT expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT: {e}")
        return None


def update_session(session_token: str, updates: dict) -> bool:
    """
    Update session data (e.g., refreshed tokens, pending actions).
    
    Args:
        session_token: JWT from session cookie
        updates: Dict of fields to update
        
    Returns:
        True if updated, False if session not found
    """
    try:
        payload = jwt.decode(
            session_token,
            settings.session_secret,
            algorithms=["HS256"]
        )
        
        session_id = payload.get("session_id")
        if session_id and session_id in _sessions:
            _sessions[session_id].update(updates)
            return True
        return False
        
    except jwt.InvalidTokenError:
        return False


def delete_session(session_token: str) -> bool:
    """
    Delete a session (logout).
    
    Args:
        session_token: JWT from session cookie
        
    Returns:
        True if deleted, False if not found
    """
    try:
        payload = jwt.decode(
            session_token,
            settings.session_secret,
            algorithms=["HS256"],
            options={"verify_exp": False}  # Allow deleting expired sessions
        )
        
        session_id = payload.get("session_id")
        if session_id and session_id in _sessions:
            email = _sessions[session_id].get("email", "unknown")
            del _sessions[session_id]
            logger.info(f"Deleted session for: {email}")
            return True
        return False
        
    except jwt.InvalidTokenError:
        return False


def is_token_expired(session: dict) -> bool:
    """
    Check if the Google access token is expired or about to expire.
    
    We consider it expired if it expires within 5 minutes,
    to give us time to refresh before actual expiry.
    
    Args:
        session: Session data dict
        
    Returns:
        True if token needs refresh
    """
    buffer = timedelta(minutes=5)
    return datetime.utcnow() + buffer > session["token_expiry"]


def update_tokens(session_token: str, access_token: str, expires_in: int) -> bool:
    """
    Update session with refreshed access token.
    
    Args:
        session_token: JWT from session cookie
        access_token: New access token
        expires_in: New expiry in seconds
        
    Returns:
        True if updated, False if session not found
    """
    return update_session(session_token, {
        "access_token": access_token,
        "token_expiry": datetime.utcnow() + timedelta(seconds=expires_in),
    })


# Dependency for protected routes
async def get_current_session(request: Request) -> dict:
    """
    FastAPI dependency to get current authenticated session.
    
    Use this as a dependency in protected routes:
    
        @router.get("/protected")
        async def protected_route(session: dict = Depends(get_current_session)):
            # session contains user info and tokens
            pass
    
    Raises:
        HTTPException 401: If not authenticated or session expired
    """
    session_cookie = request.cookies.get("session")
    
    if not session_cookie:
        raise HTTPException(
            status_code=401,
            detail={"error": True, "code": "AUTH_REQUIRED", "message": "Authentication required"}
        )
    
    session = get_session(session_cookie)
    
    if not session:
        raise HTTPException(
            status_code=401,
            detail={"error": True, "code": "SESSION_EXPIRED", "message": "Session expired. Please sign in again."}
        )
    
    # Check if access token needs refresh
    if is_token_expired(session):
        # Import here to avoid circular dependency
        from app.integrations.google_auth import refresh_access_token
        from app.utils.errors import PermissionRevokedError
        
        try:
            new_token, expires_in = await refresh_access_token(session["refresh_token"])
            update_tokens(session_cookie, new_token, expires_in)
            session["access_token"] = new_token
            logger.info(f"Refreshed token for: {session['email']}")
        except PermissionRevokedError:
            delete_session(session_cookie)
            raise HTTPException(
                status_code=401,
                detail={"error": True, "code": "PERMISSION_REVOKED", "message": "Gmail access was revoked. Please sign in again."}
            )
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise HTTPException(
                status_code=401,
                detail={"error": True, "code": "TOKEN_REFRESH_FAILED", "message": "Failed to refresh session. Please sign in again."}
            )
    
    return session


# Utility to get session ID from token (for updates)
def get_session_id(session_token: str) -> Optional[str]:
    """Extract session ID from JWT without full validation."""
    try:
        payload = jwt.decode(
            session_token,
            settings.session_secret,
            algorithms=["HS256"],
            options={"verify_exp": False}
        )
        return payload.get("session_id")
    except jwt.InvalidTokenError:
        return None


class SessionService:
    """Session service class for compatibility with route imports."""
    
    @staticmethod
    def create_session(*args, **kwargs):
        return create_session(*args, **kwargs)
    
    @staticmethod
    def get_session(*args, **kwargs):
        return get_session(*args, **kwargs)
    
    @staticmethod
    def delete_session(*args, **kwargs):
        return delete_session(*args, **kwargs)
