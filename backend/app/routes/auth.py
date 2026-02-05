"""
Authentication routes for Google OAuth.

OAuth Flow:
1. Frontend calls GET /api/auth/login → gets OAuth URL
2. Frontend redirects user to OAuth URL
3. User grants permissions on Google
4. Google redirects to GET /api/auth/callback with code
5. Backend exchanges code for tokens, creates session
6. Backend redirects to frontend /dashboard with session cookie

Security:
- Session token is HTTP-only cookie (prevents XSS)
- SameSite=None + Secure for cross-origin cookies
- Tokens stored server-side, not in JWT
"""
from fastapi import APIRouter, Response, Request, HTTPException
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.services.auth_service import AuthService
from app.services.session_service import delete_session, get_session
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()
auth_service = AuthService()


@router.get("/login")
async def login():
    """
    Get Google OAuth login URL.
    
    Frontend should:
    1. Call this endpoint
    2. Redirect user to the returned auth_url
    
    Returns:
        { auth_url: "https://accounts.google.com/..." }
    """
    try:
        auth_url = auth_service.get_oauth_url()
        logger.info("OAuth login URL generated")
        return {"auth_url": auth_url}
    except Exception as e:
        logger.error(f"Failed to generate OAuth URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate login")


@router.get("/callback")
async def oauth_callback(code: str = None, error: str = None):
    """
    Handle Google OAuth callback.
    
    This endpoint is called by Google after user grants/denies permissions.
    
    On success:
    - Exchange code for tokens
    - Create session with user info
    - Set session cookie
    - Redirect to /dashboard
    
    On error:
    - Redirect to /login with error message
    
    Query params:
        code: Authorization code from Google (on success)
        error: Error message from Google (on denial)
    """
    # Handle user denial or OAuth errors
    if error:
        logger.warning(f"OAuth error: {error}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=oauth_denied"
        )
    
    # Validate code parameter
    if not code:
        logger.warning("OAuth callback missing code")
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=missing_code"
        )
    
    try:
        # Exchange code for tokens and create session
        logger.info(f"Exchange code: {code[:10]}...")
        session_token = await auth_service.handle_oauth_callback(code)
        
        logger.info("OAuth callback successful, session created")
        
        # Create redirect response to dashboard
        response = RedirectResponse(
            url=f"{settings.frontend_url}/dashboard",
            status_code=302
        )
        
        # Determine secure flag based on environment
        # Localhost over HTTP should NOT use secure=True
        is_secure = "https" in settings.frontend_url and "localhost" not in settings.frontend_url
        
        # Set session cookie
        response.set_cookie(
            key="session",
            value=session_token,
            httponly=True,
            secure=is_secure,
            samesite="lax",  # Safer for localhost
            max_age=settings.session_expire_hours * 3600,
            path="/",
        )
        
        logger.info(f"Setting cookie: secure={is_secure}, samesite=lax")
        return response
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        logger.error(f"OAuth callback failed: {error_msg}")
        traceback.print_exc()  # Print to terminal
        
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=auth_failed&detail={error_msg}"
        )


@router.post("/logout")
async def logout(request: Request, response: Response):
    """
    Logout user by clearing session.
    
    - Deletes session from server store
    - Clears session cookie
    
    Returns:
        { success: true, message: "Logged out successfully" }
    """
    session_cookie = request.cookies.get("session")
    
    if session_cookie:
        delete_session(session_cookie)
    
    # Clear the cookie
    response.delete_cookie(
        key="session",
        path="/",
        secure=True,
        samesite="none",
    )
    
    logger.info("User logged out")
    return {"success": True, "message": "Logged out successfully"}


@router.get("/session")
async def get_session_info(request: Request):
    """
    Check current session status.
    
    Returns:
        { authenticated: true/false, email?: string }
    """
    session_cookie = request.cookies.get("session")
    
    if not session_cookie:
        return {"authenticated": False}
    
    session = get_session(session_cookie)
    
    if not session:
        return {"authenticated": False}
    
    return {
        "authenticated": True,
        "email": session["email"],
        "name": session["name"],
    }


@router.get("/refresh")
async def refresh_session(request: Request, response: Response):
    """
    Refresh the session token if needed.
    
    Called by frontend to proactively refresh before expiry.
    
    Returns:
        { refreshed: true/false, valid: true/false }
    """
    session_cookie = request.cookies.get("session")
    
    if not session_cookie:
        raise HTTPException(status_code=401, detail="No session found")
    
    try:
        # Validate and optionally refresh the session
        new_token = await auth_service.refresh_session(session_cookie)
        
        if new_token:
            # Token was refreshed, update cookie
            response.set_cookie(
                key="session",
                value=new_token,
                httponly=True,
                secure=True,
                samesite="none",
                max_age=settings.session_expire_hours * 3600,
                path="/",
            )
            return {"refreshed": True, "valid": True}
        
        return {"refreshed": False, "valid": True}
        
    except Exception as e:
        logger.error(f"Session refresh failed: {e}")
        raise HTTPException(status_code=401, detail="Session invalid or expired")
