"""
Logging configuration for the MDT Agent System.
"""
import logging
import sys

# Correct the config import
from mdt_agent_system.app.core.config.settings import settings

# Use settings object directly
LOG_LEVEL = settings.LOG_LEVEL
LOG_DIR = settings.LOG_DIR

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "mdt_agent_system.app.core.logging.logger.JSONFormatter"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "level": LOG_LEVEL
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "json",
            "filename": f"{LOG_DIR}/mdt_agent.log",
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8",
            "level": LOG_LEVEL
        }
    },
    "root": {
        "handlers": ["console", "file"],
        "level": LOG_LEVEL
    },
    "loggers": {
        "uvicorn": {
            "handlers": ["console", "file"],
            "level": LOG_LEVEL,
            "propagate": False
        },
        "fastapi": {
            "handlers": ["console", "file"],
            "level": LOG_LEVEL,
            "propagate": False
        }
    }
} 