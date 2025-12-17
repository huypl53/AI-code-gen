"""Logging configuration using structlog."""

import logging
import sys
from pathlib import Path
from typing import Any

import structlog

from app.config import settings


def configure_logging() -> None:
    """Configure structured logging for the application."""
    # Ensure log directory exists and set up handlers for both stdout and file output
    project_root = Path(__file__).resolve().parents[2]
    log_dir = Path(settings.log_directory)
    if not log_dir.is_absolute():
        log_dir = project_root / log_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / settings.log_file_name

    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding="utf-8"),
    ]

    # Set up standard library logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, settings.log_level),
        handlers=handlers,
    )

    # Configure structlog
    processors: list[Any] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Add renderer based on format
    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)
