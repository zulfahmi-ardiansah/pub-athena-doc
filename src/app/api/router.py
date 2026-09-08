import logging
from pathlib import Path
import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from fastapi.responses import JSONResponse

from src.config.settings import Settings, get_settings
from src.config.logging import get_request_id
from src.config.telemetry import async_trace_span
from src.domain.registry import DocumentRegistry
from src.app.api.deps import get_engine_singleton, get_registry
from src.engines.base import BaseExtractionEngine, ExtractionResult, ExtractionError
from src.engines.factory import create_engine
from src.utility.trace_utils import save_request_trace, sanitize_trace, delete_request_trace

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health/live", tags=["System"])
async def liveness_probe() -> Dict[str, Any]:
    """Lightweight Kubernetes / Docker container liveness probe."""
    return {"status": "alive"}


@router.get("/health/ready", tags=["System"])
async def readiness_probe(
    settings: Settings = Depends(get_settings),
    engine: BaseExtractionEngine = Depends(get_engine_singleton),
) -> JSONResponse:
    """
    Readiness probe verifying engine singleton, disk write availability
    for logs and trace folders.
    """
    checks: Dict[str, Any] = {}
    is_ready = True

    # 1. Check Engine Singleton
    try:
        checks["engine"] = {"status": "ready", "name": engine.name}
    except Exception as err:
        checks["engine"] = {"status": "error", "detail": str(err)}
        is_ready = False

    # 2. Check Log Directory Writability
    try:
        log_dir = Path(settings.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        test_file = log_dir / ".health_check_write"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        checks["log_storage"] = {"status": "ready", "path": str(log_dir)}
    except Exception as err:
        checks["log_storage"] = {"status": "error", "detail": str(err)}
        is_ready = False

    # 3. Check Trace Directory Writability
    try:
        trace_dir = Path(settings.trace_dir)
        trace_dir.mkdir(parents=True, exist_ok=True)
        checks["trace_storage"] = {"status": "ready", "path": str(trace_dir)}
    except Exception as err:
        checks["trace_storage"] = {"status": "error", "detail": str(err)}
        is_ready = False

    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if is_ready else "unready",
            "checks": checks,
        }
    )


@router.get("/health", tags=["System"])
async def health_check(settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    """Comprehensive service health, active engine, and telemetry status."""
    text_provider = settings.get_text_provider_type()
    vision_provider = settings.get_vision_provider_type()
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "active_engine": settings.engine_type,
        "ocr_backend": settings.ocr_backend,
        "llm_provider": settings.llm_provider,
        "llm_text_provider": text_provider,
        "llm_vision_provider": vision_provider,
        "extraction_pipeline": settings.extraction_pipeline,
        "analysis_mode": settings.analysis_mode,
        "keep_trace_artifacts": settings.keep_trace_artifacts,
        "otel_enabled": settings.otel_enabled,
        "pi_masking_enabled": settings.pi_masking_enabled,
        "pdp_masking_enabled": settings.pi_masking_enabled,
        "ollama_text_model": settings.ollama_text_model if text_provider == "ollama" else None,
        "ollama_vision_model": settings.ollama_vision_model if vision_provider == "ollama" else None,
        "google_text_model": settings.google_text_model if text_provider == "google" else None,
        "google_vision_model": settings.google_vision_model if vision_provider == "google" else None,
    }



@router.get("/api/v1/documents", tags=["Documents"])
async def list_documents(registry: DocumentRegistry = Depends(get_registry)) -> Dict[str, Any]:
    """Lists all supported document types, descriptions, and JSON schemas."""
    docs = []
    for doc_meta in registry.list_documents():
        doc_obj = registry.get(doc_meta["slug"])
        docs.append({
            **doc_meta,
            "json_schema": doc_obj.get_json_schema() if doc_obj else {}
        })
    return {"documents": docs}


@router.post("/api/v1/extract/{document_type}", tags=["Extraction"])
async def extract_document(
    document_type: str,
    file: UploadFile = File(...),
    trace: bool = Query(default=False, description="Include stage-by-stage evolution trace in response JSON"),
    keep_trace: Optional[bool] = Query(default=None, description="Persist trace artifacts folder on disk after success (overrides KEEP_TRACE_ARTIFACTS setting)"),
    engine: Optional[str] = Query(default=None, description="Optional engine override: 'string_engine', 'visual_engine', 'hybrid_engine'"),
    analysis_mode: Optional[str] = Query(default=None, description="Optional analysis mode override: 'text_llm', 'string'"),
    pipeline: Optional[str] = Query(default=None, description="Optional extraction pipeline override (comma-separated, e.g. 'digital_pdf,ocr')"),
    registry: DocumentRegistry = Depends(get_registry),
    default_engine: BaseExtractionEngine = Depends(get_engine_singleton),
    settings: Settings = Depends(get_settings),
) -> Any:
    """
    Extract structured JSON from uploaded document (PDF or Image).
    Supports engine, pipeline, analysis mode, and trace retention overrides per-request.
    """
    doc_spec = registry.get(document_type)
    if not doc_spec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown document_type: '{document_type}'. Check /api/v1/documents for supported types."
        )

    file_bytes = await file.read()
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.max_file_size_mb}MB"
        )

    # Use existing request_id from context or generate new UUID
    request_id = get_request_id() or str(uuid.uuid4())
    effective_keep_trace = keep_trace if keep_trace is not None else settings.keep_trace_artifacts

    # Determine active engine instance
    active_engine = default_engine
    if engine and engine.lower() != settings.engine_type.lower():
        try:
            temp_settings = settings.model_copy(update={"engine_type": engine.lower()})
            active_engine = create_engine(temp_settings)
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid engine override '{engine}': {err}"
            )

    pipeline_override_list = [s.strip().lower() for s in pipeline.split(",") if s.strip()] if pipeline else None

    async with async_trace_span("extract_document", {
        "document.type": document_type,
        "document.filename": file.filename or "unknown",
        "document.size_bytes": len(file_bytes),
        "engine.name": active_engine.name,
    }):
        try:
            # Trace is always captured during execution
            kwargs: Dict[str, Any] = {"trace": True}
            if hasattr(active_engine, "pipeline") or active_engine.name == "hybrid_engine":
                if pipeline_override_list:
                    kwargs["pipeline_override"] = pipeline_override_list
                if analysis_mode:
                    mode_lower = analysis_mode.lower()
                    kwargs["analysis_mode_override"] = "text_llm" if mode_lower in ("llm", "text_llm") else mode_lower

            result = await active_engine.extract(
                file_bytes=file_bytes,
                filename=file.filename,
                content_type=file.content_type,
                document=doc_spec,
                **kwargs,
            )

            response_payload: Dict[str, Any] = {
                "success": True,
                "request_id": request_id,
                "document_type": document_type,
                "filename": file.filename,
                "data": result.data
            }

            # Trace artifacts are always created on disk for the request
            saved_trace_dir = None
            sanitized_trace = None
            try:
                saved_trace_dir, sanitized_trace = save_request_trace(
                    request_id=request_id,
                    file_bytes=file_bytes,
                    filename=file.filename,
                    document_type=document_type,
                    extraction_result=result,
                    trace_base_dir=settings.trace_dir
                )
            except Exception as trace_err:
                logger.warning(f"Failed to save trace to disk: {trace_err}")

            # If retention is disabled on success, delete the trace folder from disk
            if saved_trace_dir is not None:
                if effective_keep_trace:
                    response_payload["trace_dir"] = str(saved_trace_dir.as_posix())
                else:
                    delete_request_trace(saved_trace_dir)

            # Include trace in response JSON only when requested (trace=true)
            if trace:
                response_payload["trace"] = sanitized_trace if sanitized_trace is not None else sanitize_trace(result.trace)

            logger.info(
                f"Extraction successful: doc_type={document_type}, filename={file.filename}, "
                f"fields_extracted={len(result.data)}"
            )
            return response_payload

        except ExtractionError as exc:
            logger.error(f"Extraction failed for {document_type} ({file.filename}): {exc.message}", exc_info=True)
            sanitized_trace = None
            trace_dir_str = None
            if exc.trace:
                try:
                    dummy_result = ExtractionResult(data=exc.raw_data or {}, trace=exc.trace)
                    saved_trace_dir, sanitized_trace = save_request_trace(
                        request_id=request_id,
                        file_bytes=file_bytes,
                        filename=file.filename,
                        document_type=document_type,
                        extraction_result=dummy_result,
                        trace_base_dir=settings.trace_dir
                    )
                    trace_dir_str = str(saved_trace_dir.as_posix())
                except Exception as trace_err:
                    logger.warning(f"Failed to save error trace to disk: {trace_err}")

                if sanitized_trace is None:
                    sanitized_trace = sanitize_trace(exc.trace)

            error_payload: Dict[str, Any] = {
                "success": False,
                "request_id": request_id,
                "document_type": document_type,
                "filename": file.filename,
                "detail": f"Extraction failed: {exc.message}",
                "error": exc.message,
            }
            if trace_dir_str:
                error_payload["trace_dir"] = trace_dir_str
            if trace and sanitized_trace is not None:
                error_payload["trace"] = sanitized_trace

            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content=error_payload
            )
        except Exception as exc:
            logger.error(f"Extraction unexpected error for {document_type} ({file.filename}): {exc}", exc_info=True)
            error_payload: Dict[str, Any] = {
                "success": False,
                "request_id": request_id,
                "document_type": document_type,
                "filename": file.filename,
                "detail": f"Extraction failed: {str(exc)}",
                "error": str(exc),
            }
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content=error_payload
            )
