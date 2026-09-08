import logging
from typing import Any
from fastapi import FastAPI, HTTPException as FastAPIHTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


from src.config.logging import get_request_id
from src.utility.pi_sanitizer import sanitize_pi_dict

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI, is_debug: bool = False) -> None:
    """Registers global exception handlers for standardized, PI-compliant error responses."""


    async def _handle_http_exception(request: Request, exc: Any) -> JSONResponse:
        req_id = get_request_id() or "-"
        status_code = getattr(exc, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)
        detail = getattr(exc, "detail", str(exc))
        logger.warning(f"HTTP {status_code} on {request.method} {request.url.path}: {detail}")
        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "request_id": req_id,
                "error": "HTTPException",
                "detail": detail,
            },
            headers=getattr(exc, "headers", None) or {}
        )


    # Register for both Starlette and FastAPI HTTP exceptions
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(FastAPIHTTPException, _handle_http_exception)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        req_id = get_request_id() or "-"
        sanitized_errors = sanitize_pi_dict(exc.errors())
        logger.warning(f"Validation error on {request.method} {request.url.path}: {sanitized_errors}")

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "request_id": req_id,
                "error": "ValidationError",
                "detail": sanitized_errors,
            }
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        req_id = get_request_id() or "-"
        logger.error(
            f"Unhandled exception on {request.method} {request.url.path} (request_id={req_id}): {exc}",
            exc_info=True
        )

        detail_msg = (
            str(exc) if is_debug
            else "An unexpected internal server error occurred. Please provide the request_id when reporting this issue."
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "request_id": req_id,
                "error": "InternalServerError",
                "detail": detail_msg,
            }
        )
