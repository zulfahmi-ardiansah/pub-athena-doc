import logging
import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from fastapi.responses import JSONResponse
from src.config.settings import Settings, get_settings
from src.domain.registry import DocumentRegistry
from src.app.api.deps import get_engine_singleton, get_registry
from src.engines.base import BaseExtractionEngine, ExtractionResult, ExtractionError
from src.engines.factory import create_engine
from src.utility.trace_utils import save_request_trace, sanitize_trace

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", tags=["System"])
async def health_check(settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    """Service health and active engine status."""
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
    trace: bool = Query(default=False, description="Include stage-by-stage evolution trace in response"),
    engine: Optional[str] = Query(default=None, description="Optional engine override: 'string_engine', 'visual_engine', 'hybrid_engine'"),
    analysis_mode: Optional[str] = Query(default=None, description="Optional analysis mode override: 'llm', 'string'"),
    pipeline: Optional[str] = Query(default=None, description="Optional extraction pipeline override (comma-separated, e.g. 'digital_pdf,ocr')"),
    registry: DocumentRegistry = Depends(get_registry),
    default_engine: BaseExtractionEngine = Depends(get_engine_singleton),
    settings: Settings = Depends(get_settings),
) -> Any:
    """
    Extract structured JSON from uploaded document (PDF or Image).
    Supports engine, pipeline, and analysis mode overrides per-request.
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

    request_id = str(uuid.uuid4())
    should_trace = trace or settings.enable_demo

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

    try:
        kwargs: Dict[str, Any] = {"trace": should_trace}
        if hasattr(active_engine, "pipeline") or active_engine.name == "hybrid_engine":
            if pipeline_override_list:
                kwargs["pipeline_override"] = pipeline_override_list
            if analysis_mode:
                kwargs["analysis_mode_override"] = analysis_mode.lower()

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

        sanitized_trace = None
        if settings.enable_demo:
            try:
                saved_trace_dir, sanitized_trace = save_request_trace(
                    request_id=request_id,
                    file_bytes=file_bytes,
                    filename=file.filename,
                    document_type=document_type,
                    extraction_result=result,
                    trace_base_dir=settings.trace_dir
                )
                response_payload["trace_dir"] = str(saved_trace_dir.as_posix())
            except Exception as trace_err:
                logger.warning(f"Failed to save trace to disk: {trace_err}")

        if trace and result.trace is not None:
            response_payload["trace"] = sanitized_trace if sanitized_trace is not None else sanitize_trace(result.trace)

        return response_payload

    except ExtractionError as exc:
        logger.error(f"Extraction failed for {document_type} ({file.filename}): {exc.message}", exc_info=True)
        sanitized_trace = None
        trace_dir_str = None
        if exc.trace:
            if settings.enable_demo:
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
        logger.error(f"Extraction failed for {document_type} ({file.filename}): {exc}", exc_info=True)
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
