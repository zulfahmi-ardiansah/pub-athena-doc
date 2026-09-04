import logging
import uuid
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from src.config.settings import Settings, get_settings
from src.domain.registry import DocumentRegistry
from src.app.api.deps import get_engine_singleton, get_registry
from src.engines.base import BaseExtractionEngine
from src.utility.trace_utils import save_request_trace, sanitize_trace

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", tags=["System"])
async def health_check(settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    """Service health and active backend status."""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "active_backend": settings.engine_backend,
        "ocr_engine": settings.ocr_engine if settings.engine_backend in ("ocr_hybrid", "local_cpu") else None,
        "ollama_model": (
            settings.ollama_vision_model if settings.engine_backend == "visual_model"
            else (settings.ollama_model if settings.engine_backend in ("ocr_hybrid", "local_cpu") else None)
        ),
        "gemini_model": settings.gemini_model if settings.engine_backend == "cloud_google" else None,
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
    registry: DocumentRegistry = Depends(get_registry),
    engine: BaseExtractionEngine = Depends(get_engine_singleton),
    settings: Settings = Depends(get_settings),
) -> Dict[str, Any]:
    """
    Extract structured JSON from uploaded document (PDF or Image).
    If trace=True, returns stage-by-stage extraction and prompt evolution.
    If demo is enabled, saves uploaded file, preprocessed/adjusted images, and trace.json to trace/{uuid}/.
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

    try:
        result = await engine.extract(
            file_bytes=file_bytes,
            filename=file.filename,
            content_type=file.content_type,
            document=doc_spec,
            trace=should_trace
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
    except Exception as exc:
        logger.error(f"Extraction failed for {document_type} ({file.filename}): {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Extraction failed: {str(exc)}"
        )
