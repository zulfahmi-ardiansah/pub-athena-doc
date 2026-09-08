from contextlib import asynccontextmanager, contextmanager
import logging
from typing import Any, AsyncGenerator, Dict, Generator, Optional, Tuple

logger = logging.getLogger(__name__)

# Track global state
_TELEMETRY_INITIALIZED = False
_TRACER_PROVIDER = None


def is_telemetry_available() -> bool:
    """Checks if OpenTelemetry SDK libraries are installed and importable."""
    try:
        import opentelemetry  # noqa: F401
        from opentelemetry.sdk.trace import TracerProvider  # noqa: F401
        return True
    except ImportError:
        return False


def get_current_trace_and_span_id() -> Tuple[Optional[str], Optional[str]]:
    """
    Returns the active OpenTelemetry (trace_id, span_id) as formatted hex strings,
    or (None, None) if telemetry is disabled or no span is active.
    """
    try:
        from opentelemetry import trace
        span = trace.get_current_span()
        if span and span.is_recording():
            ctx = span.get_span_context()
            if ctx and ctx.is_valid:
                trace_id = format(ctx.trace_id, "032x")
                span_id = format(ctx.span_id, "016x")
                return trace_id, span_id
    except Exception:
        pass
    return None, None


def setup_telemetry(app: Any, settings: Any) -> None:
    """
    Initializes OpenTelemetry TracerProvider, OTLP Span Exporter, W3C TraceContext
    propagation, and automatic FastAPI/HTTPX instrumentations.
    """
    global _TELEMETRY_INITIALIZED, _TRACER_PROVIDER

    if not settings.otel_enabled:
        logger.info("OpenTelemetry is disabled (OTEL_ENABLED=false). Tracing will operate in no-op mode.")
        return

    if not is_telemetry_available():
        logger.warning("OpenTelemetry packages not found. Distributed tracing skipped.")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
        from opentelemetry.propagate import set_global_textmap

        # Configure resource attributes
        resource = Resource.create({
            "service.name": settings.otel_service_name,
            "service.version": settings.otel_service_version,
            "deployment.environment": "development" if settings.debug else "production",
        })

        provider = TracerProvider(resource=resource)

        # Set up OTLP Exporter if endpoint configured
        endpoint = settings.otel_exporter_otlp_endpoint
        if endpoint:
            if settings.otel_exporter_otlp_protocol == "http/protobuf":
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                exporter = OTLPSpanExporter(endpoint=endpoint)
            else:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
                exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)

            processor = BatchSpanProcessor(exporter)
            provider.add_span_processor(processor)
            logger.info(f"OpenTelemetry OTLP Exporter configured -> {endpoint} ({settings.otel_exporter_otlp_protocol})")

        # Set global TracerProvider and W3C TextMap Propagator
        trace.set_tracer_provider(provider)
        set_global_textmap(TraceContextTextMapPropagator())
        _TRACER_PROVIDER = provider

        # Instrument FastAPI
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            FastAPIInstrumentor.instrument_app(
                app,
                tracer_provider=provider,
                excluded_urls="health,health/live,health/ready,static/*,favicon.ico"
            )
            logger.info("FastAPI OpenTelemetry instrumentation activated.")
        except Exception as e:
            logger.warning(f"Failed to auto-instrument FastAPI: {e}")

        # Instrument HTTPX
        try:
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
            HTTPXClientInstrumentor().instrument(tracer_provider=provider)
            logger.info("HTTPX OpenTelemetry instrumentation activated.")
        except Exception as e:
            logger.warning(f"Failed to auto-instrument HTTPX: {e}")

        _TELEMETRY_INITIALIZED = True
        logger.info(f"OpenTelemetry successfully initialized for '{settings.otel_service_name}'.")

    except Exception as exc:
        logger.error(f"Failed to initialize OpenTelemetry: {exc}", exc_info=True)


def shutdown_telemetry() -> None:
    """Flushes and shuts down OpenTelemetry TracerProvider."""
    global _TRACER_PROVIDER, _TELEMETRY_INITIALIZED
    if _TRACER_PROVIDER is not None:
        try:
            _TRACER_PROVIDER.shutdown()
            logger.info("OpenTelemetry TracerProvider shut down cleanly.")
        except Exception as err:
            logger.warning(f"Error shutting down TracerProvider: {err}")
        finally:
            _TRACER_PROVIDER = None
            _TELEMETRY_INITIALIZED = False


@contextmanager
def trace_span(name: str, attributes: Optional[Dict[str, Any]] = None) -> Generator[Any, None, None]:
    """
    Synchronous context manager for tracing custom code blocks or stage operations.
    Falls back cleanly to a no-op if OpenTelemetry is disabled.
    """
    if not _TELEMETRY_INITIALIZED:
        yield None
        return

    try:
        from opentelemetry import trace
        tracer = trace.get_tracer("athena-doc-extractor")
        with tracer.start_as_current_span(name) as span:
            if attributes:
                for k, v in attributes.items():
                    if isinstance(v, (str, int, float, bool)):
                        span.set_attribute(k, v)
                    else:
                        span.set_attribute(k, str(v))
            yield span
    except Exception:
        yield None


@asynccontextmanager
async def async_trace_span(name: str, attributes: Optional[Dict[str, Any]] = None) -> AsyncGenerator[Any, None]:
    """
    Asynchronous context manager for tracing async operations (e.g. LLM calls, async engines).
    """
    if not _TELEMETRY_INITIALIZED:
        yield None
        return

    try:
        from opentelemetry import trace
        tracer = trace.get_tracer("athena-doc-extractor")
        with tracer.start_as_current_span(name) as span:
            if attributes:
                for k, v in attributes.items():
                    if isinstance(v, (str, int, float, bool)):
                        span.set_attribute(k, v)
                    else:
                        span.set_attribute(k, str(v))
            yield span
    except Exception:
        yield None
