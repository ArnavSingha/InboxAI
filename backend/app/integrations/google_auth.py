"""
Google OAuth client integration.

This module handles:
1. Generating OAuth authorization URLs
2. Exchanging authorization codes for tokens
3. Refreshing expired access tokens
4. Fetching user profile information
"""
import httpx
from typing import Optional, Tuple
from urllib.parse import urlencode

from app.config import get_settings
from app.utils.logger import get_logger
from app.utils.errors import AuthError, PermissionRevokedError

logger = get_logger(__name__)
settings = get_settings()

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def get_oauth_url() -> str:
    """
    Generate Google OAuth authorization URL.
    
    The user will be redirected to this URL to grant permissions.
    After granting, Google redirects back to our callback with a code.
    
    Returns:
        OAuth authorization URL string
    """
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(settings.google_scopes),
        "access_type": "offline",  # Request refresh token
        "prompt": "consent",  # Force consent to get refresh token
        "include_granted_scopes": "true",
    }
    
    url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    logger.info("Generated OAuth URL")
    return url


async def exchange_code_for_tokens(code: str) -> dict:
    """
    Exchange authorization code for access and refresh tokens.
    
    This is step 2 of the OAuth flow. After user grants permission,
    Google redirects with a code. We exchange this code for tokens.
    
    Args:
        code: Authorization code from Google callback
        
    Returns:
        Dict with access_token, refresh_token, expires_in
        
    Raises:
        AuthError: If token exchange fails
    """
    data = {
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.google_redirect_uri,
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(GOOGLE_TOKEN_URL, data=data)
            
            if response.status_code != 200:
                error_data = response.json()
                logger.error(f"Token exchange failed: {error_data}")
                print(f"\n[CRITICAL] GOOGLE TOKEN ERROR: {error_data}\n") # Print to terminal
                raise AuthError(f"Failed to exchange code: {error_data.get('error_description', 'Unknown error')}")
            
            tokens = response.json()
            logger.info("Successfully exchanged code for tokens")
            
            return {
                "access_token": tokens["access_token"],
                "refresh_token": tokens.get("refresh_token"),  # May not be present on re-auth
                "expires_in": tokens.get("expires_in", 3600),
            }
            
        except httpx.RequestError as e:
            logger.error(f"Token exchange request failed: {e}")
            raise AuthError("Failed to connect to Google for authentication")


async def refresh_access_token(refresh_token: str) -> Tuple[str, int]:
    """
    Refresh an expired access token using the refresh token.
    
    Access tokens expire after ~1 hour. We use the refresh token
    to get a new access token without requiring user interaction.
    
    Args:
        refresh_token: The refresh token from initial auth
        
    Returns:
        Tuple of (new_access_token, expires_in_seconds)
        
    Raises:
        PermissionRevokedError: If refresh token is invalid/revoked
        AuthError: For other refresh failures
    """
    data = {
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(GOOGLE_TOKEN_URL, data=data)
            
            if response.status_code != 200:
                error_data = response.json()
                error_code = error_data.get("error", "")
                
                # Check for revoked permissions
                if error_code == "invalid_grant":
                    logger.warning("Refresh token revoked or expired")
                    raise PermissionRevokedError()
                
                logger.error(f"Token refresh failed: {error_data}")
                raise AuthError("Failed to refresh access token")
            
            tokens = response.json()
            logger.info("Successfully refreshed access token")
            
            return tokens["access_token"], tokens.get("expires_in", 3600)
            
        except httpx.RequestError as e:
            logger.error(f"Token refresh request failed: {e}")
            raise AuthError("Failed to connect to Google for token refresh")


async def get_user_info(access_token: str) -> dict:
    """
    Fetch user profile information from Google.
    
    Args:
        access_token: Valid Google access token
        
    Returns:
        Dict with id, email, name, picture
        
    Raises:
        AuthError: If request fails or token is invalid
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(GOOGLE_USERINFO_URL, headers=headers)
            
            if response.status_code == 401:
                logger.warning("Access token invalid when fetching user info")
                raise AuthError("Access token is invalid")
            
            if response.status_code != 200:
                logger.error(f"Failed to get user info: {response.status_code}")
                raise AuthError("Failed to fetch user information")
            
            user_data = response.json()
            logger.info(f"Fetched user info for: {user_data.get('email', 'unknown')}")
            
            return {
                "id": user_data["id"],
                "email": user_data["email"],
                "name": user_data.get("name", user_data["email"]),
                "picture": user_data.get("picture"),
            }
            
        except httpx.RequestError as e:
            logger.error(f"User info request failed: {e}")
            raise AuthError("Failed to connect to Google for user information")
