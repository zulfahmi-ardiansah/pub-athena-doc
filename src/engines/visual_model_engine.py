import base64
import logging
from typing import Any, Dict, List, Optional, Tuple
import fitz  # PyMuPDF
from src.domain.base import BaseDocument
from src.engines.base import BaseExtractionEngine, ExtractionResult, ExtractionError
from src.providers.base import BaseLLMProvider
from src.utility.pdf_utils import is_pdf
from src.utility.image_utils import (
    is_image,
    normalize_image_bytes,
    preprocess_image_bytes,
)

logger = logging.getLogger(__name__)


class VisualModelEngine(BaseExtractionEngine):
    """
    Pure Visual Model extraction engine:
    1. Multi-page PDF to rendered high-res image pages / Image normalization.
    2. Image preprocessing: deskewing, background whitening/contrast enhancement, thresholding.
    3. Sends document image bytes directly to Ollama vision models (e.g. llama3.2-vision, qwen2.5-vl, minicpm-v, deepseek-vl).
    4. Structured JSON extraction constrained by JSON Schema natively on Ollama.
    """

    name = "visual_model"

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        render_dpi: int = 150,
        preprocess: bool = True,
        deskew: bool = True,
        enhance_contrast: bool = True,
        threshold_mode: Optional[str] = "none",
        gamma: float = 1.15,
        white_cutoff: int = 230,
        black_level: int = 25
    ) -> None:
        self.llm_provider = llm_provider
        self.render_dpi = render_dpi
        self.preprocess = preprocess
        self.deskew = deskew
        self.enhance_contrast = enhance_contrast
        self.threshold_mode = threshold_mode or "none"
        self.gamma = gamma
        self.white_cutoff = white_cutoff
        self.black_level = black_level

    async def warmup(self) -> None:
        """Preloads Vision LLM model into memory."""
        if hasattr(self.llm_provider, "preload"):
            await self.llm_provider.preload()

    def _render_pdf_to_images(self, pdf_bytes: bytes) -> List[bytes]:
        """Renders every page of a PDF into high-res PNG image bytes."""
        image_list: List[bytes] = []
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            zoom = self.render_dpi / 72.0
            matrix = fitz.Matrix(zoom, zoom)
            for page in doc:
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                image_list.append(pix.tobytes("png"))
        finally:
            doc.close()
        return image_list

    def _preprocess_image(self, image_bytes: bytes) -> Tuple[bytes, Dict[str, Any]]:
        """Applies configured image preprocessing pipeline (deskew, contrast, thresholding)."""
        if not self.preprocess:
            return image_bytes, {"preprocessing_enabled": False}
        return preprocess_image_bytes(
            image_bytes=image_bytes,
            deskew=self.deskew,
            enhance_contrast_enabled=self.enhance_contrast,
            threshold_mode=self.threshold_mode,
            gamma=self.gamma,
            white_cutoff=self.white_cutoff,
            black_level=self.black_level
        )

    async def extract(
        self,
        file_bytes: bytes,
        filename: Optional[str],
        content_type: Optional[str],
        document: BaseDocument,
        trace: bool = False
    ) -> ExtractionResult:
        stages: List[Dict[str, Any]] = []

        if not file_bytes:
            err_msg = "Empty file provided for extraction"
            if trace:
                stages.append({
                    "stage": 1,
                    "name": "visual_render_triage",
                    "status": "failed",
                    "details": {"error": err_msg}
                })
            raise ExtractionError(
                message=err_msg,
                trace={"engine": self.name, "stages": stages} if trace else None
            )

        image_bytes_list: List[bytes] = []
        detected_format = "unknown"
        pages_summary: List[Dict[str, Any]] = []

        try:
            if is_pdf(content_type, filename):
                detected_format = "pdf"
                raw_rendered_images = self._render_pdf_to_images(file_bytes)
                for idx, page_raw_bytes in enumerate(raw_rendered_images, start=1):
                    processed_bytes, prep_meta = self._preprocess_image(page_raw_bytes)
                    image_bytes_list.append(processed_bytes)
                    pages_summary.append({
                        "page": idx,
                        "type": "pdf_rendered_page",
                        "render_dpi": self.render_dpi,
                        "preprocessing": prep_meta
                    })
            elif is_image(content_type, filename):
                detected_format = "image"
                norm_bytes, dims = normalize_image_bytes(file_bytes)
                processed_bytes, prep_meta = self._preprocess_image(norm_bytes)
                image_bytes_list.append(processed_bytes)
                pages_summary.append({
                    "page": 1,
                    "type": "image_page",
                    "dimensions": dims,
                    "preprocessing": prep_meta
                })
            else:
                detected_format = "fallback_image"
                try:
                    norm_bytes, dims = normalize_image_bytes(file_bytes)
                    processed_bytes, prep_meta = self._preprocess_image(norm_bytes)
                    image_bytes_list.append(processed_bytes)
                    pages_summary.append({
                        "page": 1,
                        "type": "fallback_image_page",
                        "dimensions": dims,
                        "preprocessing": prep_meta
                    })
                except Exception:
                    image_bytes_list.append(file_bytes)
                    pages_summary.append({
                        "page": 1,
                        "type": "raw_image_fallback",
                        "preprocessing": {"preprocessing_enabled": False}
                    })

            if not image_bytes_list:
                raise ValueError("Could not extract or render visual content from document")
        except Exception as exc:
            if trace:
                stages.append({
                    "stage": 1,
                    "name": "visual_render_triage",
                    "status": "failed",
                    "details": {
                        "filename": filename,
                        "content_type": content_type,
                        "detected_format": detected_format,
                        "error": str(exc),
                        "error_type": exc.__class__.__name__
                    }
                })
            raise ExtractionError(
                message=str(exc),
                trace={"engine": self.name, "stages": stages} if trace else None
            ) from exc

        if trace:
            stages.append({
                "stage": 1,
                "name": "visual_render_triage",
                "status": "completed",
                "details": {
                    "filename": filename,
                    "content_type": content_type,
                    "detected_format": detected_format,
                    "rendered_pages_count": len(image_bytes_list),
                    "render_dpi": self.render_dpi,
                    "preprocessing_enabled": self.preprocess,
                    "pages": pages_summary
                }
            })

        # Encode image list to base64 strings
        base64_images = [
            base64.b64encode(img_bytes).decode("utf-8")
            for img_bytes in image_bytes_list
        ]

        system_prompt = document.build_system_prompt()
        json_schema = document.get_json_schema()
        fields_list = ", ".join(json_schema.get("properties", {}).keys())
        user_prompt = (
            f"Carefully examine the attached {document.name} ({document.description}) image.\n"
            f"Extract every printed field into the JSON object: {fields_list}.\n"
            f"Follow all extraction and disambiguation rules defined in the system prompt."
        )

        if trace:
            stages.append({
                "stage": 2,
                "name": "multimodal_prompt_construction",
                "status": "completed",
                "details": {
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "attached_images_count": len(base64_images),
                    "target_json_schema": json_schema
                }
            })

        try:
            raw_json_dict = await self.llm_provider.generate_structured(
                prompt=user_prompt,
                json_schema=json_schema,
                system_prompt=system_prompt,
                images=base64_images
            )
        except Exception as exc:
            if trace:
                stages.append({
                    "stage": 3,
                    "name": "vision_llm_structured_output",
                    "status": "failed",
                    "details": {
                        "provider": getattr(self.llm_provider, "name", "ollama"),
                        "model": getattr(self.llm_provider, "model", "unknown"),
                        "error": str(exc),
                        "error_type": exc.__class__.__name__
                    }
                })
            raise ExtractionError(
                message=str(exc),
                trace={"engine": self.name, "stages": stages} if trace else None
            ) from exc

        if trace:
            stages.append({
                "stage": 3,
                "name": "vision_llm_structured_output",
                "status": "completed",
                "details": {
                    "provider": getattr(self.llm_provider, "name", "ollama"),
                    "model": getattr(self.llm_provider, "model", "unknown"),
                    "raw_llm_json": raw_json_dict
                }
            })

        # Validate through domain schema class
        try:
            validated_model = document.validate_payload(raw_json_dict)
            final_data = validated_model.model_dump()
        except Exception as exc:
            if trace:
                stages.append({
                    "stage": 4,
                    "name": "schema_validation",
                    "status": "failed",
                    "details": {
                        "schema_class": document.schema_class.__name__,
                        "error": str(exc),
                        "error_type": exc.__class__.__name__,
                        "raw_input": raw_json_dict
                    }
                })
            raise ExtractionError(
                message=str(exc),
                trace={"engine": self.name, "stages": stages} if trace else None,
                raw_data=raw_json_dict if isinstance(raw_json_dict, dict) else None
            ) from exc

        if trace:
            stages.append({
                "stage": 4,
                "name": "schema_validation",
                "status": "completed",
                "details": {
                    "schema_class": document.schema_class.__name__,
                    "validated_fields": list(final_data.keys()),
                    "final_output": final_data
                }
            })

        trace_data = {"engine": self.name, "stages": stages} if trace else None
        return ExtractionResult(data=final_data, trace=trace_data)
