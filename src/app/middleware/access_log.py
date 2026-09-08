import logging
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.config.logging import set_request_id, set_correlation_id
from src.config.telemetry import get_current_trace_and_span_id

access_logger = logging.getLogger("athena.access")


def get_client_ip(request: Request) -> str:
    """Extracts client IP address accounting for reverse proxies."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


class AccessLogMiddleware(BaseHTTPMiddleware):
    """
    Middleware that:
    1. Extracts or generates X-Request-ID and X-Correlation-ID.
    2. Sets context variables for structured logging across async handlers.
    3. Tracks request execution latency in milliseconds.
    4. Records structured HTTP access logs into logs/access.log and stdout.
    5. Injects X-Request-ID, X-Correlation-ID, and X-Trace-ID into HTTP response headers.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # 1. Resolve Request ID & Correlation ID
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        corr_id = request.headers.get("X-Correlation-ID") or req_id

        # Set context variables for this async task
        set_request_id(req_id)
        set_correlation_id(corr_id)

        client_ip = get_client_ip(request)
        method = request.method
        path = request.url.path
        query = str(request.url.query) if request.url.query else ""
        user_agent = request.headers.get("user-agent", "-")

        start_time = time.perf_counter()

        try:
            response: Response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            raise
        finally:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            trace_id, span_id = get_current_trace_and_span_id()

            # Record access log entry with structured metadata
            access_logger.info(
                f"{client_ip} - \"{method} {path}{'?' + query if query else ''}\" "
                f"{status_code} {duration_ms}ms",
                extra={
                    "http": {
                        "method": method,
                        "path": path,
                        "query": query,
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                        "client_ip": client_ip,
                        "user_agent": user_agent,
                    }
                }
            )

        # Inject tracing and correlation headers into outgoing response
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Correlation-ID"] = corr_id
        if trace_id:
            response.headers["X-Trace-ID"] = trace_id

        return response
