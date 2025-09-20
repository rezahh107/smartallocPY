"""Logging configuration helpers for the application."""

from __future__ import annotations

import logging
import logging.config
from typing import Any, Dict

from .settings import get_settings


LOGGING_CONFIG: Dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "DEBUG",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}


def configure_logging() -> None:
    """Configure logging using the default configuration and settings."""

    settings = get_settings()
    logging.config.dictConfig(LOGGING_CONFIG)
    logging.getLogger().setLevel(settings.log_level.upper())
