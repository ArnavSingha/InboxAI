"""
Custom error classes for the application.
"""
from typing import Optional


class AppError(Exception):
    """Base application error."""
    
    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN_ERROR",
        status_code: int = 500,
        details: Optional[dict] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """Convert error to dictionary for response."""
        return {
            "error": True,
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


class AuthError(AppError):
    """Authentication related errors."""
    
    def __init__(self, message: str, code: str = "AUTH_ERROR"):
        super().__init__(message, code, status_code=401)


class SessionExpiredError(AuthError):
    """Session has expired."""
    
    def __init__(self):
        super().__init__(
            "Your session has expired. Please sign in again.",
            "SESSION_EXPIRED"
        )


class PermissionRevokedError(AuthError):
    """Gmail permissions were revoked."""
    
    def __init__(self):
        super().__init__(
            "Gmail access was revoked. Please sign in and grant permissions again.",
            "PERMISSION_REVOKED"
        )


class GmailError(AppError):
    """Gmail API related errors."""
    
    def __init__(self, message: str = "Couldn't reach Gmail. Please try again."):
        super().__init__(message, "GMAIL_ERROR", status_code=503)


class AIError(AppError):
    """AI service related errors."""
    
    def __init__(self, message: str = "AI processing failed. Please try again."):
        super().__init__(message, "AI_ERROR", status_code=503)


class EmailNotFoundError(AppError):
    """Email not found."""
    
    def __init__(self, reference: str = ""):
        message = f"Couldn't find email matching '{reference}'." if reference else "Email not found."
        super().__init__(message, "EMAIL_NOT_FOUND", status_code=404)


class InvalidRequestError(AppError):
    """Invalid request format."""
    
    def __init__(self, message: str = "Invalid request format."):
        super().__init__(message, "INVALID_REQUEST", status_code=400)


class RateLimitError(AppError):
    """Rate limit exceeded."""
    
    def __init__(self):
        super().__init__(
            "Too many requests. Please wait a moment.",
            "RATE_LIMITED",
            status_code=429
        )
