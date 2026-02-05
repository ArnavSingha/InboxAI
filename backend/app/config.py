"""
Application configuration loaded from environment variables.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/callback"
    
    # Frontend URL for CORS and redirects
    frontend_url: str = "http://localhost:3000"
    
    # Gemini AI
    gemini_api_key: str = ""
    
    # Session
    session_secret: str = "dev-secret-change-in-production"
    session_expire_hours: int = 24
    
    # Debug mode
    debug: bool = True
    
    # Google OAuth scopes
    @property
    def google_scopes(self) -> list[str]:
        return [
            "openid",
            "email",
            "profile",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.modify",
        ]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
