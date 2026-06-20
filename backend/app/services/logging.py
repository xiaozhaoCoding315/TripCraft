"""
TripCraft Structured Logging Service

Provides JSON-formatted logging for production environments.
Includes request tracking, performance metrics, and error reporting.
"""

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.config import Settings, get_settings

# Context variable for request ID
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request ID if available
        req_id = request_id_var.get()
        if req_id:
            log_entry["request_id"] = req_id

        # Add extra fields if present
        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data

        # Add exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        return json.dumps(log_entry, ensure_ascii=False)


class TripCraftLogger:
    """Enhanced logger with context tracking"""

    def __init__(self, name: str):
        self._logger = logging.getLogger(name)

    def _log(self, level: int, message: str, **kwargs: Any) -> None:
        extra = {"extra_data": kwargs} if kwargs else {}
        self._logger.log(level, message, extra=extra)

    def info(self, message: str, **kwargs: Any) -> None:
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self._log(logging.ERROR, message, **kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        self._log(logging.DEBUG, message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        self._log(logging.CRITICAL, message, **kwargs)


def setup_logging(settings: Settings) -> None:
    """Configure application logging"""
    # Determine log level
    log_level = logging.DEBUG if settings.app_env == "development" else logging.INFO

    # Create console handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Suppress noisy loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Log startup message
    logger = TripCraftLogger("tripcraft")
    logger.info(
        "Logging configured",
        app_env=settings.app_env,
        log_level=logging.getLevelName(log_level),
    )


def get_logger(name: str) -> TripCraftLogger:
    """Get a logger instance"""
    return TripCraftLogger(name)


def set_request_id(request_id: Optional[str] = None) -> str:
    """Set or generate request ID for current context"""
    if request_id is None:
        request_id = str(uuid.uuid4())[:8]
    request_id_var.set(request_id)
    return request_id


def get_request_id() -> Optional[str]:
    """Get current request ID"""
    return request_id_var.get()


class RequestTimer:
    """Context manager for timing requests"""

    def __init__(self, operation: str, logger: TripCraftLogger):
        self.operation = operation
        self.logger = logger
        self.start_time: float = 0

    def __enter__(self) -> "RequestTimer":
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        duration_ms = (time.time() - self.start_time) * 1000
        if exc_type is None:
            self.logger.info(
                f"{self.operation} completed",
                duration_ms=round(duration_ms, 2),
            )
        else:
            self.logger.error(
                f"{self.operation} failed",
                duration_ms=round(duration_ms, 2),
                error=str(exc_val),
            )
