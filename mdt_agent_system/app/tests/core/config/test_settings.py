import os
import pytest
from typing import List, Union
from pydantic import AnyHttpUrl, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from mdt_agent_system.app.core.config.settings import Settings
from dotenv import set_key, find_dotenv

# Fixture to manage environment variables during tests
@pytest.fixture(autouse=True)
def manage_env_vars():
    original_environ = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(original_environ)

def test_settings_from_env_vars():
    """Test settings loaded from environment variables."""
    # Set test environment variables
    os.environ["GEMINI_API_KEY"] = "test-api-key"
    os.environ["LOG_LEVEL"] = "DEBUG"

    settings = Settings()
    assert settings.GEMINI_API_KEY == "test-api-key"
    assert settings.LOG_LEVEL == "DEBUG"

def test_settings_defaults():
    """Test default settings values when no env vars are set."""
    # Create a test instance that won't load from .env
    class TestSettings(BaseSettings):
        GEMINI_API_KEY: str = Field(...)
        model_config = SettingsConfigDict(env_file=None)
    
    # Clear environment variables
    os.environ.clear()
    
    # Expect validation error because GEMINI_API_KEY is required
    with pytest.raises(ValidationError):
        TestSettings()

def test_allowed_origins_default():
    """Test default CORS allowed origins."""
    os.environ["GEMINI_API_KEY"] = "dummy-key"
    settings = Settings()
    assert len(settings.ALLOWED_ORIGINS) == 2
    assert "http://localhost:8000" in settings.ALLOWED_ORIGINS
    assert "http://localhost:3000" in settings.ALLOWED_ORIGINS
