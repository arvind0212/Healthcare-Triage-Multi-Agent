import json
import logging
import logging.handlers
import os
import uuid
from datetime import datetime, UTC
from typing import Dict, Any
from mdt_agent_system.app.core.config import get_config
import contextvars

# Define context variable for run_id
run_id_context = contextvars.ContextVar("run_id", default=None)

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging, includes context variables."""

    def __init__(self):
        super().__init__()
        # Trace ID could potentially be set via contextvar as well if needed per-request
        self.trace_id = str(uuid.uuid4())

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON"""
        # Start with base log data
        log_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "trace_id": self.trace_id # Process-level trace ID
        }

        # Add run_id from context variable if set
        run_id = run_id_context.get()
        if run_id:
            log_data["run_id"] = run_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from record attributes
        for key, value in record.__dict__.items():
            if key not in ["args", "asctime", "created", "exc_info", "exc_text", 
                         "filename", "funcName", "levelname", "levelno", "lineno",
                         "module", "msecs", "msg", "name", "pathname", "process",
                         "processName", "relativeCreated", "stack_info", "thread",
                         "threadName", "trace_id"] and key not in log_data:
                log_data[key] = value
        
        return json.dumps(log_data, default=str) # Use default=str for non-serializable types

def close_all_handlers() -> None:
    """Close all handlers on the root logger"""
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        handler.close()
        root_logger.removeHandler(handler)

def setup_logging() -> None:
    """Setup logging configuration"""
    config = get_config()
    
    # Create log directory if it doesn't exist
    os.makedirs(config.LOG_DIR, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(config.LOG_LEVEL)
    
    # Remove existing handlers
    close_all_handlers()
    
    # Create file handler with rotation
    log_file = os.path.join(config.LOG_DIR, "mdt_agent.log")
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        mode='a',  # Append mode
        encoding='utf-8'
    )
    file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(file_handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)
    
    # Log initial message to verify file creation
    root_logger.info(f"Logging initialized. Log file: {log_file}")

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name"""
    return logging.getLogger(name) 