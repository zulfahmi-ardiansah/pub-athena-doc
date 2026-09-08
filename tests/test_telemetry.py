import pytest
from fastapi import FastAPI
from src.config.telemetry import (
    is_telemetry_available,
    setup_telemetry,
    shutdown_telemetry,
    trace_span,
    async_trace_span,
    get_current_trace_and_span_id,
)
from src.config.settings import Settings


def test_telemetry_availability():
    # Verify is_telemetry_available returns a boolean without throwing exceptions
    assert isinstance(is_telemetry_available(), bool)


def test_trace_span_when_disabled():
    shutdown_telemetry()
    trace_id, span_id = get_current_trace_and_span_id()
    assert trace_id is None
    assert span_id is None

    # Sync span when disabled should gracefully no-op
    with trace_span("test.sync_span", {"test_key": "test_val"}) as span:
        assert span is None


@pytest.mark.asyncio
async def test_async_trace_span_when_disabled():
    shutdown_telemetry()
    async with async_trace_span("test.async_span", {"test_key": "test_val"}) as span:
        assert span is None


@pytest.mark.skipif(not is_telemetry_available(), reason="OpenTelemetry SDK packages not installed")
def test_telemetry_lifecycle_and_spans():
    app = FastAPI()
    settings = Settings(
        otel_enabled=True,
        otel_service_name="test-telemetry-service",
        otel_exporter_otlp_endpoint=None,  # No remote collector in unit tests
    )

    try:
        setup_telemetry(app, settings)

        # Inside active span, trace_id and span_id should be populated
        with trace_span("test.active_operation", {"doc.type": "ktp"}) as span:
            assert span is not None
            trace_id, span_id = get_current_trace_and_span_id()
            assert trace_id is not None
            assert len(trace_id) == 32  # 128-bit hex string
            assert span_id is not None
            assert len(span_id) == 16   # 64-bit hex string

        # Outside span, current span is inactive
        trace_id_after, span_id_after = get_current_trace_and_span_id()
        assert trace_id_after is None
    finally:
        shutdown_telemetry()

