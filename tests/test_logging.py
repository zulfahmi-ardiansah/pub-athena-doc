import json
import logging
from pathlib import Path
import shutil
import tempfile
import pytest

from src.config.logging import (
    JSONFormatter,
    ColoredConsoleFormatter,
    ContextEnrichmentFilter,
    get_request_id,
    set_request_id,
    get_correlation_id,
    set_correlation_id,
    setup_logging,
    flush_logging_handlers,
)
from src.config.settings import Settings


def test_json_formatter():
    formatter = JSONFormatter(service_name="test-service")
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="Document extracted successfully",
        args=(),
        exc_info=None
    )
    record.request_id = "req-12345"
    record.correlation_id = "corr-67890"

    formatted = formatter.format(record)
    parsed = json.loads(formatted)

    assert parsed["level"] == "INFO"
    assert parsed["service"] == "test-service"
    assert parsed["logger"] == "test_logger"
    assert parsed["message"] == "Document extracted successfully"
    assert parsed["request_id"] == "req-12345"
    assert parsed["correlation_id"] == "corr-67890"
    assert parsed["source"]["line"] == 42
    assert "timestamp" in parsed


def test_json_formatter_with_exception():
    formatter = JSONFormatter(service_name="test-service")
    try:
        raise ValueError("Invalid NIK number 3201011205900001")
    except Exception as exc:
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Extraction failed",
            args=(),
            exc_info=(type(exc), exc, exc.__traceback__)
        )
        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        assert parsed["level"] == "ERROR"
        assert "exception" in parsed
        assert parsed["exception"]["type"] == "ValueError"
        # PDP masking in traceback
        assert "3201011205900001" not in parsed["exception"]["stacktrace"]
        assert "320101******0001" in parsed["exception"]["stacktrace"]


def test_context_vars_and_filter():
    set_request_id("req-abc-999")
    set_correlation_id("corr-xyz-888")

    assert get_request_id() == "req-abc-999"
    assert get_correlation_id() == "corr-xyz-888"

    ctx_filter = ContextEnrichmentFilter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test",
        args=(),
        exc_info=None
    )
    ctx_filter.filter(record)

    assert getattr(record, "request_id") == "req-abc-999"
    assert getattr(record, "correlation_id") == "corr-xyz-888"

    set_request_id(None)
    set_correlation_id(None)



def test_setup_logging_creates_tiered_files():
    temp_dir = tempfile.mkdtemp()
    try:
        settings = Settings(
            log_dir=temp_dir,
            log_level="DEBUG",
            log_format="json",
            log_to_file=True,
            pdp_masking_enabled=True,
        )
        setup_logging(settings)

        test_logger = logging.getLogger("app.test")
        access_logger = logging.getLogger("athena.access")

        test_logger.info("Application starting info")
        test_logger.warning("Warning event detected")
        test_logger.error("Error event occurred")
        access_logger.info("GET /api/v1/documents 200 5ms")

        flush_logging_handlers()

        log_path = Path(temp_dir)
        app_log = log_path / "app.log"
        error_log = log_path / "error.log"
        access_log = log_path / "access.log"

        assert app_log.exists(), "app.log must exist"
        assert error_log.exists(), "error.log must exist"
        assert access_log.exists(), "access.log must exist"

        app_content = app_log.read_text(encoding="utf-8")
        error_content = error_log.read_text(encoding="utf-8")
        access_content = access_log.read_text(encoding="utf-8")

        # app.log contains info, warning, error
        assert "Application starting info" in app_content
        assert "Warning event detected" in app_content
        assert "Error event occurred" in app_content

        # error.log contains warning and error, NOT info
        assert "Application starting info" not in error_content
        assert "Warning event detected" in error_content
        assert "Error event occurred" in error_content

        # access.log contains HTTP access entry
        assert "GET /api/v1/documents 200 5ms" in access_content

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
