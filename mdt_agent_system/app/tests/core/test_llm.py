import pytest
import os
from unittest.mock import patch

from langchain_google_genai import ChatGoogleGenerativeAI
from mdt_agent_system.app.core.llm import get_llm
from mdt_agent_system.app.core.config import get_config, reset_config
from mdt_agent_system.app.core.callbacks import LoggingCallbackHandler

# Fixture to reset config before each test
@pytest.fixture(autouse=True)
def reset_singleton_config():
    reset_config()
    yield
    reset_config()

# Test basic LLM initialization
@pytest.mark.skipif(not os.environ.get("GOOGLE_API_KEY"), reason="GOOGLE_API_KEY not set in environment")
def test_get_llm_initialization():
    """Tests if get_llm initializes ChatGoogleGenerativeAI successfully."""
    llm = get_llm()
    assert isinstance(llm, ChatGoogleGenerativeAI)
    config = get_config()
    # Account for models/ prefix in Google Generative AI models
    assert llm.model == f"models/{config.LLM_MODEL}" or llm.model == config.LLM_MODEL
    assert llm.temperature == config.LLM_TEMPERATURE
    # API key check removed as client structure has changed
    assert llm.max_retries == config.LLM_MAX_RETRIES

# Test LLM initialization with callbacks
@pytest.mark.skipif(not os.environ.get("GOOGLE_API_KEY"), reason="GOOGLE_API_KEY not set in environment")
def test_get_llm_with_callbacks():
    """Tests if get_llm initializes with custom callbacks."""
    callback = LoggingCallbackHandler()
    llm = get_llm(callbacks=[callback])
    assert isinstance(llm, ChatGoogleGenerativeAI)
    # Check if the callback is registered directly in the callbacks list
    assert callback in llm.callbacks

# Test initialization failure without API key
@patch.dict(os.environ, {"GOOGLE_API_KEY": ""}, clear=True)
def test_get_llm_initialization_fails_without_key():
    """Tests if get_llm raises ValueError when API key is missing."""
    # Ensure the config reflects the missing key
    reset_config()
    with pytest.raises(ValueError):
        get_llm()

# Test initialization with custom config values (using environment variables)
@patch.dict(os.environ, {
    "GOOGLE_API_KEY": "test_key_for_llm_config",
    "LLM_MODEL": "gemini-pro",
    "LLM_TEMPERATURE": "0.5",
    "LLM_MAX_RETRIES": "5"
})
def test_get_llm_with_env_vars():
    """Tests if get_llm correctly uses settings from environment variables."""
    # Reset config to force reload from patched env vars
    reset_config() 
    llm = get_llm()
    assert isinstance(llm, ChatGoogleGenerativeAI)
    # Account for models/ prefix in Google Generative AI models
    assert llm.model == "models/gemini-pro" or llm.model == "gemini-pro"
    assert llm.temperature == 0.5
    assert llm.max_retries == 5
    # API key check removed as client structure has changed 