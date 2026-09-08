import copy
import json
import logging
from pathlib import Path
import shutil
from typing import Any, Dict, Optional, Tuple
from src.engines.base import ExtractionResult

logger = logging.getLogger(__name__)


def delete_request_trace(trace_dir: Path) -> None:
    """
    Removes a request trace directory and all its contents from disk.
    Called on successful extraction when trace persistence is disabled.
    """
    try:
        if trace_dir.exists() and trace_dir.is_dir():
            shutil.rmtree(trace_dir, ignore_errors=True)
            logger.info(f"Cleaned up request trace directory: {trace_dir}")
    except Exception as err:
        logger.warning(f"Failed to cleanup trace directory {trace_dir}: {err}")


def sanitize_trace(trace: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Recursively sanitizes a trace dictionary to ensure all values are JSON-serializable,
    replacing raw binary bytes with safe representation strings.
    """
    if trace is None:
        return None

    def _sanitize(val: Any) -> Any:
        if isinstance(val, bytes):
            return f"<{len(val)} bytes binary data>"
        elif isinstance(val, dict):
            return {k: _sanitize(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [_sanitize(item) for item in val]
        return val

    return _sanitize(copy.deepcopy(trace))


def save_request_trace(
    request_id: str,
    file_bytes: bytes,
    filename: Optional[str],
    document_type: str,
    extraction_result: ExtractionResult,
    trace_base_dir: str = "trace"
) -> Tuple[Path, Optional[Dict[str, Any]]]:
    """
    Persists request trace artifacts to disk under {trace_base_dir}/{request_id}/:
    1. Original uploaded file (e.g. original_<filename>).
    2. Image results from threshold, deskew, and contrast adjustments.
    3. Structured trace.json with stage evolutions, prompts, and extracted JSON.

    Returns (trace_dir_path, sanitized_trace_dict).
    """
    trace_dir = Path(trace_base_dir) / request_id
    trace_dir.mkdir(parents=True, exist_ok=True)

    # 1. Save original uploaded file
    safe_filename = Path(filename).name if filename else "uploaded_document"
    uploaded_file_path = trace_dir / f"original_{safe_filename}"
    uploaded_file_path.write_bytes(file_bytes)

    # 2. Extract and save processed images from trace
    trace_dict = copy.deepcopy(extraction_result.trace) if extraction_result.trace else {}

    saved_images = []
    if isinstance(trace_dict, dict) and "stages" in trace_dict:
        for stage in trace_dict.get("stages", []):
            details = stage.get("details", {})
            if isinstance(details, dict) and "pages" in details:
                for page_info in details["pages"]:
                    page_num = page_info.get("page", 1)
                    prep = page_info.get("preprocessing", {})
                    if isinstance(prep, dict) and "images" in prep:
                        images_dict = prep["images"]
                        if isinstance(images_dict, dict):
                            for img_stage, img_data in list(images_dict.items()):
                                if isinstance(img_data, bytes):
                                    img_filename = f"page_{page_num}_{img_stage}.png"
                                    img_path = trace_dir / img_filename
                                    img_path.write_bytes(img_data)
                                    saved_images.append(img_filename)
                                    # Replace bytes with relative filename in trace JSON
                                    images_dict[img_stage] = img_filename

    # Ensure any other possible bytes in trace are cleanly sanitized
    sanitized_trace = sanitize_trace(trace_dict)

    # 3. Save trace.json
    trace_summary: Dict[str, Any] = {
        "request_id": request_id,
        "document_type": document_type,
        "filename": filename,
        "uploaded_file": uploaded_file_path.name,
        "saved_images": saved_images,
        "data": extraction_result.data,
        "trace": sanitized_trace
    }

    trace_json_path = trace_dir / "trace.json"
    with open(trace_json_path, "w", encoding="utf-8") as f:
        json.dump(trace_summary, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved trace artifacts to {trace_dir}")
    return trace_dir, sanitized_trace
