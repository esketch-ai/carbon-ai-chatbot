"""Structured logging configuration for the CarbonAI Agent.

This module provides JSON-formatted logging for production environments
and human-readable logging for development. It supports contextual
information like request_id, user_id, and other metadata.

Usage:
    from react_agent.logging_config import setup_logging, get_logger, LogContext

    # At application startup
    setup_logging()

    # Get a logger
    logger = get_logger(__name__)

    # Log with context
    with LogContext(request_id="abc123", user_id="user1"):
        logger.info("Processing request")
"""

import os
import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from contextvars import ContextVar

# Context variable for storing log context (thread-safe)
_log_context: ContextVar[Dict[str, Any]] = ContextVar("log_context", default={})


class LogContext:
    """Context manager for adding contextual information to logs.

    Usage:
        with LogContext(request_id="abc123", user_id="user1"):
            logger.info("Processing request")  # Will include request_id and user_id

    Can be nested - inner contexts will merge with outer contexts.
    """

    def __init__(self, **kwargs: Any):
        """Initialize with context key-value pairs."""
        self.new_context = kwargs
        self.previous_context: Dict[str, Any] = {}

    def __enter__(self) -> "LogContext":
        """Enter the context, merging new context with existing."""
        self.previous_context = _log_context.get().copy()
        merged_context = {**self.previous_context, **self.new_context}
        _log_context.set(merged_context)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the context, restoring previous context."""
        _log_context.set(self.previous_context)


def get_log_context() -> Dict[str, Any]:
    """Get the current log context."""
    return _log_context.get().copy()


def set_log_context(**kwargs: Any) -> None:
    """Set log context values directly (useful for middleware)."""
    current = _log_context.get().copy()
    current.update(kwargs)
    _log_context.set(current)


def clear_log_context() -> None:
    """Clear the current log context."""
    _log_context.set({})


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging in production.

    Outputs log records as single-line JSON objects with:
    - timestamp: ISO 8601 format in UTC
    - level: Log level name
    - logger: Logger name
    - message: Log message
    - module: Source module name
    - function: Source function name
    - line: Source line number
    - context: Any contextual information (request_id, user_id, etc.)
    - exception: Exception details if present
    - extra: Any extra fields passed to the log call
    """

    # Fields that are standard LogRecord attributes (not extra fields)
    RESERVED_ATTRS = {
        "name", "msg", "args", "created", "filename", "funcName",
        "levelname", "levelno", "lineno", "module", "msecs",
        "pathname", "process", "processName", "relativeCreated",
        "stack_info", "exc_info", "exc_text", "thread", "threadName",
        "taskName", "message",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        # Build the base log object
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add context from ContextVar
        context = get_log_context()
        if context:
            log_obj["context"] = context

        # Add any extra fields passed to the log call
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in self.RESERVED_ATTRS:
                try:
                    # Ensure value is JSON serializable
                    json.dumps(value)
                    extra_fields[key] = value
                except (TypeError, ValueError):
                    extra_fields[key] = str(value)

        if extra_fields:
            log_obj["extra"] = extra_fields

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Add stack info if present
        if record.stack_info:
            log_obj["stack_info"] = record.stack_info

        return json.dumps(log_obj, ensure_ascii=False, default=str)


class DevelopmentFormatter(logging.Formatter):
    """Human-readable formatter for development environments.

    Includes colors (if terminal supports it) and structured context output.
    """

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
    }
    RESET = "\033[0m"

    def __init__(self, use_colors: bool = True):
        """Initialize with optional color support."""
        super().__init__()
        self.use_colors = use_colors and _supports_color()

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record in a human-readable way."""
        # Format timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Format level with color if enabled
        level = record.levelname
        if self.use_colors:
            color = self.COLORS.get(level, "")
            level_str = f"{color}{level:8s}{self.RESET}"
        else:
            level_str = f"{level:8s}"

        # Build base message
        message = record.getMessage()
        base = f"{timestamp} {level_str} [{record.name}] {message}"

        # Add context if present
        context = get_log_context()
        if context:
            context_str = " ".join(f"{k}={v}" for k, v in context.items())
            base = f"{base} | {context_str}"

        # Add exception if present
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            base = f"{base}\n{exc_text}"

        return base


def _supports_color() -> bool:
    """Check if the terminal supports colors."""
    # Check for NO_COLOR environment variable (standard)
    if os.getenv("NO_COLOR"):
        return False

    # Check for FORCE_COLOR environment variable
    if os.getenv("FORCE_COLOR"):
        return True

    # Check if stdout is a TTY
    import sys
    if not hasattr(sys.stdout, "isatty"):
        return False

    return sys.stdout.isatty()


def setup_logging(
    level: Optional[str] = None,
    force_json: bool = False,
    force_development: bool = False,
) -> None:
    """Set up logging configuration based on environment.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Defaults to LOG_LEVEL env var or INFO.
        force_json: Always use JSON format regardless of environment.
        force_development: Always use development format regardless of environment.
    """
    # Determine log level
    log_level_str = level or os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Determine format based on environment
    is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"

    if force_json:
        use_json = True
    elif force_development:
        use_json = False
    else:
        use_json = is_production

    # Create handler
    handler = logging.StreamHandler()

    if use_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(DevelopmentFormatter())

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers = []  # Clear existing handlers
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "format": "json" if use_json else "development",
            "level": log_level_str,
            "environment": "production" if is_production else "development",
        }
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.

    This is a convenience function that returns a standard Python logger.
    The logger will automatically include contextual information when
    used within a LogContext.

    Args:
        name: Logger name (typically __name__)

    Returns:
        logging.Logger instance
    """
    return logging.getLogger(name)


# Middleware helper for FastAPI
class RequestContextMiddleware:
    """FastAPI middleware to add request context to logs.

    Usage:
        from react_agent.logging_config import RequestContextMiddleware

        app = FastAPI()
        app.add_middleware(RequestContextMiddleware)
    """

    def __init__(self, app: Any):
        """Initialize middleware with app."""
        self.app = app

    async def __call__(self, scope: Dict[str, Any], receive: Any, send: Any) -> None:
        """Process request and add context."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import uuid

        # Generate request ID
        request_id = str(uuid.uuid4())[:8]

        # Extract useful info from scope
        path = scope.get("path", "")
        method = scope.get("method", "")

        # Set context for this request
        set_log_context(
            request_id=request_id,
            path=path,
            method=method,
        )

        try:
            await self.app(scope, receive, send)
        finally:
            # Clear context after request
            clear_log_context()
