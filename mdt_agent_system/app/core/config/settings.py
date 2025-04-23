import os
import pathlib
from dotenv import load_dotenv
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, Field, validator, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env file before defining the Settings class
# Determine the correct directory (assuming settings.py is 3 levels down from mdt_agent_system)
# Healthcare-Triage-Multi-Agent/mdt_agent_system/app/core/config/settings.py
_mdt_system_dir = pathlib.Path(__file__).resolve().parent.parent.parent.parent
_dotenv_path = _mdt_system_dir / '.env'

print(f"[settings.py] Attempting to load .env file from: {_dotenv_path}")
_loaded = load_dotenv(dotenv_path=_dotenv_path, override=True)
if not _loaded:
    print(f"[settings.py] Warning: .env file not found at {_dotenv_path}")
else:
    print("[settings.py] .env file loaded successfully.")


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
    GOOGLE_API_KEY: str = Field(..., min_length=1, description="API Key for Google AI (Gemini)")

    # LLM Configuration
    LLM_MODEL: str = Field(default="gemini-1.5-flash-latest", description="Name of the Gemini model to use")
    LLM_TEMPERATURE: float = Field(default=0.7, ge=0.0, le=1.0, description="LLM temperature (0.0 to 1.0)")
    LLM_MAX_RETRIES: int = Field(default=2, ge=0, description="Maximum number of retries for LLM calls")

    # CORS Origins
    ALLOWED_ORIGINS: List[Union[AnyHttpUrl, str]] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="List of allowed CORS origins"
    )

    # Optional settings
    LOG_LEVEL: Optional[str] = Field(default="INFO", description="Logging level")
    LOG_DIR: str = Field(default="logs", description="Directory to store log files")
    MEMORY_DIR: str = Field(default="memory_data", description="Directory to store persistent memory files (e.g., status, agent memory)")

    @field_validator('LOG_LEVEL')
    @classmethod
    def validate_log_level(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if value.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return value.upper()

    # Use SettingsConfigDict for modern Pydantic v2 configuration
    model_config = SettingsConfigDict(
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
    print(f"  GOOGLE_API_KEY: {'*' * 8 if settings.GOOGLE_API_KEY else 'Not Set'}")
    print(f"  LLM_MODEL: {settings.LLM_MODEL}")
    print(f"  LLM_TEMPERATURE: {settings.LLM_TEMPERATURE}")
    print(f"  LLM_MAX_RETRIES: {settings.LLM_MAX_RETRIES}")
    print(f"  ALLOWED_ORIGINS: {settings.ALLOWED_ORIGINS}")
    print(f"  LOG_LEVEL: {settings.LOG_LEVEL}")
    print(f"  LOG_DIR: {settings.LOG_DIR}")
    print(f"  MEMORY_DIR: {settings.MEMORY_DIR}")
