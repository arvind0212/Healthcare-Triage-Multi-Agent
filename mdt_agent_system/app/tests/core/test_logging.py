import json
import logging
import os
import tempfile
import pytest
import importlib # Needed to reload modules

from mdt_agent_system.app.core.logging.logger import JSONFormatter, setup_logging, get_logger, close_all_handlers
from mdt_agent_system.app.core.config.settings import settings
from mdt_agent_system.app.core.logging import log_config, logger as logger_module # Import modules for reloading

@pytest.fixture
def temp_log_dir():
    """Provides a temporary directory for log files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture(autouse=True)
def cleanup_logging():
    """Ensures logging handlers are closed after each test."""
    yield
    close_all_handlers()


def test_logging_setup(monkeypatch, temp_log_dir):
    """Test that setup_logging configures file and console handlers correctly based on settings."""
    log_file = os.path.join(temp_log_dir, "mdt_agent.log")

    # --- Test with DEBUG level --- 
    monkeypatch.setenv("LOG_DIR", temp_log_dir)
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    # Ensure settings are reloaded if modules were already imported
    importlib.reload(logger_module)
    importlib.reload(log_config)

    # Setup logging using the patched environment
    setup_logging()
    
    test_logger = get_logger("test_debug_logger")
    # Verify DEBUG messages are logged to file
    test_logger.debug("This is a debug message.")
    test_logger.info("This is an info message.")
    close_all_handlers() # Close to flush file

    assert os.path.exists(log_file)
    with open(log_file, "r", encoding="utf-8") as f:
        log_content = f.read()
        assert "This is a debug message." in log_content
        assert "This is an info message." in log_content
    os.remove(log_file) # Clean up log file for next part

    # --- Test with WARNING level --- 
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    # Reload modules to pick up new env var
    importlib.reload(logger_module)
    importlib.reload(log_config)

    setup_logging()
    test_logger = get_logger("test_warning_logger")
    test_logger.debug("This debug should NOT be logged.")
    test_logger.info("This info should NOT be logged.")
    test_logger.warning("This is a warning message.")
    close_all_handlers()

    assert os.path.exists(log_file)
    with open(log_file, "r", encoding="utf-8") as f:
        log_content = f.read()
        assert "This debug should NOT be logged." not in log_content
        assert "This info should NOT be logged." not in log_content
        assert "This is a warning message." in log_content

def test_json_formatter():
    """Test JSON formatter formats log records correctly."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    formatted = formatter.format(record)
    data = json.loads(formatted)
    
    assert "timestamp" in data
    assert data["level"] == "INFO"
    assert data["message"] == "Test message"
    assert data["module"] == "test"
    assert "trace_id" in data

def test_logger_hierarchy():
    """Test logger hierarchy setup."""
    # No monkeypatch needed if just testing hierarchy
    try:
        # Reload modules in case previous test changed level
        importlib.reload(logger_module)
        importlib.reload(log_config)
        setup_logging()
        
        parent_logger = get_logger("parent")
        child_logger = get_logger("parent.child")
        
        assert child_logger.parent is parent_logger
        assert child_logger.name == "parent.child"
    finally:
        close_all_handlers() 