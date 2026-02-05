"""
Authentication service.

This module orchestrates the OAuth flow:
1. Generate OAuth URL → google_auth
2. Handle callback → exchange code → get user → create session
3. Refresh sessions when needed
"""
from typing import Optional

from app.integrations.google_auth import (
    get_oauth_url as _get_oauth_url,
    exchange_code_for_tokens,
    get_user_info,
    refresh_access_token,
)
from app.services.session_service import (
    create_session,
    get_session,
    update_tokens,
    is_token_expired,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AuthService:
    """
    Authentication service handling OAuth flow.
    
    Usage:
        auth_service = AuthService()
        url = auth_service.get_oauth_url()
        token = await auth_service.handle_oauth_callback(code)
    """
    
    def get_oauth_url(self) -> str:
        """
        Get the Google OAuth authorization URL.
        
        Frontend should redirect user to this URL.
        
        Returns:
            OAuth URL string
        """
        return _get_oauth_url()
    
    async def handle_oauth_callback(self, code: str) -> str:
        """
        Handle OAuth callback after user grants permission.
        
        Flow:
        1. Exchange authorization code for tokens
        2. Fetch user profile from Google
        3. Create session with tokens and user info
        
        Args:
            code: Authorization code from Google callback
            
        Returns:
            Session token (JWT) to store in cookie
            
        Raises:
            AuthError: If any step fails
        """
        # Step 1: Exchange code for tokens
        tokens = await exchange_code_for_tokens(code)
        logger.info("Exchanged code for tokens")
        
        # Step 2: Get user info
        user_info = await get_user_info(tokens["access_token"])
        logger.info(f"Got user info for: {user_info['email']}")
        
        # Step 3: Create session
        session_token = create_session(
            user_id=user_info["id"],
            email=user_info["email"],
            name=user_info["name"],
            picture=user_info.get("picture"),
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            expires_in=tokens["expires_in"],
        )
        
        return session_token
    
    async def refresh_session(self, session_token: str) -> Optional[str]:
        """
        Refresh session if access token is expired.
        
        Args:
            session_token: Current session JWT
            
        Returns:
            New session token if refreshed, None if not needed
            
        Raises:
            AuthError: If session invalid or refresh fails
        """
        session = get_session(session_token)
        
        if not session:
            from app.utils.errors import AuthError
            raise AuthError("Session not found or expired")
        
        if not is_token_expired(session):
            # Token is still valid, no refresh needed
            return None
        
        # Refresh the token
        new_access_token, expires_in = await refresh_access_token(
            session["refresh_token"]
        )
        
        update_tokens(session_token, new_access_token, expires_in)
        logger.info(f"Refreshed session for: {session['email']}")
        
        # Return same token (JWT hasn't changed, only stored data)
        return session_token
