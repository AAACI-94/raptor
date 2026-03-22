"""Structured logging with bracketed service prefix."""

import logging
import sys

from app.core.config import settings


class BracketedFormatter(logging.Formatter):
    """Format log messages with bracketed service prefix for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "service"):
            record.service = record.name.split(".")[-1]  # type: ignore[attr-defined]
        return super().format(record)


def setup_logging() -> None:
    """Configure structured logging for the application."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    formatter = BracketedFormatter(
        fmt="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    # Quiet noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("opentelemetry").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
