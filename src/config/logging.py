from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import sys
import traceback
from typing import Any, Dict, Optional

from src.utility.pi_sanitizer import PILoggingFilter, sanitize_pi_string
from src.config.telemetry import get_current_trace_and_span_id

# Context variables for request and correlation tracking across async tasks
_request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_correlation_id_ctx: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def get_request_id() -> Optional[str]:
    """Retrieves current request ID from context."""
    return _request_id_ctx.get()


def set_request_id(req_id: Optional[str]) -> None:
    """Sets current request ID in context."""
    _request_id_ctx.set(req_id)


def get_correlation_id() -> Optional[str]:
    """Retrieves current correlation ID from context."""
    return _correlation_id_ctx.get()


def set_correlation_id(corr_id: Optional[str]) -> None:
    """Sets current correlation ID in context."""
    _correlation_id_ctx.set(corr_id)


class ContextEnrichmentFilter(logging.Filter):
    """
    Enriches each LogRecord with request_id, correlation_id, and active OpenTelemetry
    trace_id / span_id for full observability correlation.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        record.correlation_id = get_correlation_id() or "-"

        trace_id, span_id = get_current_trace_and_span_id()
        record.trace_id = trace_id or "-"
        record.span_id = span_id or "-"
        return True


class JSONFormatter(logging.Formatter):
    """
    Structured JSON Lines formatter formatted for enterprise log ingestion (ELK, Vector, Loki, CloudWatch).
    """

    def __init__(self, service_name: str = "athena-doc-extractor"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        # Construct ISO8601 UTC timestamp
        record_time = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()

        log_data: Dict[str, Any] = {
            "timestamp": record_time,
            "level": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "correlation_id": getattr(record, "correlation_id", "-"),
            "trace_id": getattr(record, "trace_id", "-"),
            "span_id": getattr(record, "span_id", "-"),
            "source": {
                "file": record.filename,
                "line": record.lineno,
                "func": record.funcName,
                "module": record.module,
            },
        }

        # Include custom extra metadata if present
        extra_keys = set(record.__dict__.keys()) - {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName",
            "processName", "process", "message", "request_id", "correlation_id",
            "trace_id", "span_id", "service"
        }
        if extra_keys:
            log_data["extra"] = {k: record.__dict__[k] for k in extra_keys}

        # Include exception trace if available
        if record.exc_info:
            exc_type, exc_val, exc_tb = record.exc_info
            if exc_tb:
                tb_lines = traceback.format_exception(exc_type, exc_val, exc_tb)
                formatted_tb = "".join(tb_lines)
                log_data["exception"] = {
                    "type": exc_type.__name__ if exc_type else "Exception",
                    "message": str(exc_val),
                    "stacktrace": sanitize_pi_string(formatted_tb),
                }

        return json.dumps(log_data, ensure_ascii=False)


class ColoredConsoleFormatter(logging.Formatter):
    """Human-readable colored console formatter for local terminal development."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[1;31m" # Bold Red
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        record_time = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        req_id = getattr(record, "request_id", "-")
        req_part = f" [{req_id}]" if req_id and req_id != "-" else ""
        
        msg = record.getMessage()
        line = f"{record_time} {color}[{record.levelname:<5}]{self.RESET}{req_part} {record.name}: {msg}"

        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
            if record.exc_text:
                line += f"\n{sanitize_pi_string(record.exc_text)}"

        return line


def setup_logging(settings: Any) -> None:
    """
    Configures unified standard library logging with tiered rotating files,
    JSON Lines formatting, Personal Information (PI) privacy protection, and request context enrichment.
    """
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    pi_enabled = getattr(settings, "pi_masking_enabled", True)
    pi_filter = PILoggingFilter(enabled=pi_enabled)
    context_filter = ContextEnrichmentFilter()

    # Base Root Logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()

    # 1. Console Stream Handler (Stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    if settings.log_format == "json":
        console_handler.setFormatter(JSONFormatter(service_name=settings.app_name))
    else:
        console_handler.setFormatter(ColoredConsoleFormatter())

    console_handler.addFilter(context_filter)
    console_handler.addFilter(pi_filter)
    root_logger.addHandler(console_handler)

    # 2. Physical File Handlers (if log_to_file is enabled)
    if settings.log_to_file:
        log_dir = Path(settings.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        json_formatter = JSONFormatter(service_name=settings.app_name)

        # A. All Events Log (`logs/app.log`) - Rotates daily at midnight
        app_file_handler = TimedRotatingFileHandler(
            filename=str(log_dir / "app.log"),
            when="midnight",
            interval=1,
            backupCount=settings.log_retention_days,
            encoding="utf-8"
        )
        app_file_handler.setLevel(log_level)
        app_file_handler.setFormatter(json_formatter)
        app_file_handler.addFilter(context_filter)
        app_file_handler.addFilter(pi_filter)
        root_logger.addHandler(app_file_handler)

        # B. Errors & Warnings Log (`logs/error.log`)
        error_file_handler = TimedRotatingFileHandler(
            filename=str(log_dir / "error.log"),
            when="midnight",
            interval=1,
            backupCount=settings.log_retention_days,
            encoding="utf-8"
        )
        error_file_handler.setLevel(logging.WARNING)
        error_file_handler.setFormatter(json_formatter)
        error_file_handler.addFilter(context_filter)
        error_file_handler.addFilter(pi_filter)
        root_logger.addHandler(error_file_handler)

        # C. HTTP Access Log (`logs/access.log`)
        access_logger = logging.getLogger("athena.access")
        access_logger.setLevel(logging.INFO)
        access_logger.propagate = False  # Keep access logs focused

        access_file_handler = TimedRotatingFileHandler(
            filename=str(log_dir / "access.log"),
            when="midnight",
            interval=1,
            backupCount=settings.log_retention_days,
            encoding="utf-8"
        )
        access_file_handler.setLevel(logging.INFO)
        access_file_handler.setFormatter(json_formatter)
        access_file_handler.addFilter(context_filter)
        access_file_handler.addFilter(pi_filter)
        access_logger.addHandler(access_file_handler)

        # Also emit access logs to console if in debug mode
        if settings.debug:
            access_logger.addHandler(console_handler)

    # Intercept standard framework loggers
    for logger_name in ("uvicorn", "uvicorn.error", "fastapi", "httpx"):
        sub_logger = logging.getLogger(logger_name)
        sub_logger.handlers.clear()
        sub_logger.propagate = True

    # Disable default raw uvicorn.access logger to avoid duplicated unformatted access logs
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers.clear()
    uvicorn_access.propagate = False

    logging.info(
        f"Standardized logging initialized: level={settings.log_level}, "
        f"format={settings.log_format}, file_logging={settings.log_to_file}, "
        f"pi_masking={pi_enabled}"
    )


def flush_logging_handlers() -> None:
    """Flushes, closes, and detaches all logging handlers during shutdown."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        try:
            handler.flush()
            handler.close()
            root.removeHandler(handler)
        except Exception:
            pass

    access = logging.getLogger("athena.access")
    for handler in list(access.handlers):
        try:
            handler.flush()
            handler.close()
            access.removeHandler(handler)
        except Exception:
            pass

