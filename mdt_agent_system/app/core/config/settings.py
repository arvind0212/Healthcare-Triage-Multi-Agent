import os
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, Field, validator, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application settings.

    Uses pydantic-settings to load from environment variables and .env files.
    """
    # Application Meta
    APP_NAME: str = Field(default="MDT Agent System", description="Name of the application")
    APP_VERSION: str = Field(default="0.1.0", description="Version of the application")
    DEBUG: bool = Field(default=False, description="Enable debug mode")

    # API Keys - Marked as required
    GEMINI_API_KEY: str = Field(..., min_length=1, description="API Key for Google Gemini")

    # CORS Origins
    ALLOWED_ORIGINS: List[Union[AnyHttpUrl, str]] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="List of allowed CORS origins"
    )

    # Optional settings
    LOG_LEVEL: Optional[str] = Field(default="INFO", description="Logging level")

    # Use SettingsConfigDict for modern Pydantic v2 configuration
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

# Instantiate settings
settings = Settings()

# Example usage (optional, for direct script execution)
if __name__ == "__main__":
    print("Settings loaded:")
    print(f"  APP_NAME: {settings.APP_NAME}")
    print(f"  APP_VERSION: {settings.APP_VERSION}")
    print(f"  DEBUG: {settings.DEBUG}")
    print(f"  GEMINI_API_KEY: {'*' * 8 if settings.GEMINI_API_KEY else 'Not Set'}")
    print(f"  ALLOWED_ORIGINS: {settings.ALLOWED_ORIGINS}")
    print(f"  LOG_LEVEL: {settings.LOG_LEVEL}")
