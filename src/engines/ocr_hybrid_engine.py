import io
import logging
from typing import Any, Dict, List, Optional
from PIL import Image
from src.domain.base import BaseDocument
from src.engines.base import BaseExtractionEngine, ExtractionResult
from src.providers.base import BaseLLMProvider
from src.utility.pdf_utils import is_pdf, inspect_and_extract_pdf_pages
from src.utility.image_utils import is_image, normalize_image_bytes

logger = logging.getLogger(__name__)


class OcrHybridEngine(BaseExtractionEngine):
    """
    OCR Hybrid extraction engine:
    1. Multi-page PDF / Image triage.
    2. Digital PDF text extraction (PyMuPDF) or OCR (RapidOCR ONNX / Tesseract).
    3. Structured JSON extraction via local LLM provider (Ollama Qwen 2.5).
    """

    name = "ocr_hybrid"

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        ocr_engine_type: str = "rapidocr",
        tesseract_cmd: Optional[str] = None
    ) -> None:
        self.llm_provider = llm_provider
        self.ocr_engine_type = (ocr_engine_type or "rapidocr").lower()
        self.tesseract_cmd = tesseract_cmd
        self._rapid_ocr = None

        if self.tesseract_cmd:
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            except ImportError:
                pass

    async def warmup(self) -> None:
        """Preloads LLM model into memory."""
        if hasattr(self.llm_provider, "preload"):
            await self.llm_provider.preload()

    def _get_rapid_ocr(self):
        """Lazy-load RapidOCR ONNX instance."""
        if self._rapid_ocr is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
                self._rapid_ocr = RapidOCR()
            except ImportError as err:
                logger.error("rapidocr-onnxruntime is not installed.")
                raise RuntimeError("RapidOCR is required for OcrHybridEngine OCR processing") from err
        return self._rapid_ocr

    def _run_ocr_on_bytes(self, image_bytes: bytes) -> str:
        """Executes selected OCR engine (RapidOCR or Tesseract) on raw image bytes."""
        if self.ocr_engine_type == "tesseract":
            try:
                import pytesseract
                if self.tesseract_cmd:
                    pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
                with Image.open(io.BytesIO(image_bytes)) as img:
                    ocr_res = pytesseract.image_to_string(img)
                    if isinstance(ocr_res, str):
                        return ocr_res.strip()
                    if isinstance(ocr_res, dict):
                        text = ocr_res.get("text") or ocr_res.get("data") or ""
                        if isinstance(text, str):
                            return text.strip()
                        if isinstance(text, list):
                            return " ".join(str(item) for item in text if item).strip()
                        return str(text).strip()
                    if isinstance(ocr_res, bytes):
                        return ocr_res.decode("utf-8", errors="ignore").strip()
                    return str(ocr_res).strip() if ocr_res else ""
            except ImportError as err:
                logger.error("pytesseract is not installed.")
                raise RuntimeError("pytesseract is required when OCR_ENGINE=tesseract") from err
            except Exception as err:
                logger.error(f"Tesseract execution error: {err}")
                raise RuntimeError(f"Tesseract OCR failed: {err}") from err
        else:
            # Default to RapidOCR
            ocr = self._get_rapid_ocr()
            result, _ = ocr(image_bytes)
            if not result:
                return ""
            return "\n".join(item[1] for item in result if len(item) > 1 and item[1]).strip()

    async def extract(
        self,
        file_bytes: bytes,
        filename: Optional[str],
        content_type: Optional[str],
        document: BaseDocument,
        trace: bool = False
    ) -> ExtractionResult:
        aggregated_text_blocks: List[str] = []
        stages: List[Dict[str, Any]] = []

        # Stage 1: File Triage & Extraction
        detected_format = "unknown"
        pages_summary = []

        if is_pdf(content_type, filename):
            detected_format = "pdf"
            pages = inspect_and_extract_pdf_pages(file_bytes)
            for page_num, digital_text, rendered_png in pages:
                if digital_text:
                    pages_summary.append({
                        "page": page_num,
                        "type": "digital_text",
                        "character_count": len(digital_text)
                    })
                    aggregated_text_blocks.append(f"--- Page {page_num} ---\n{digital_text}")
                elif rendered_png:
                    ocr_text = self._run_ocr_on_bytes(rendered_png)
                    pages_summary.append({
                        "page": page_num,
                        "type": f"scanned_image_ocr ({self.ocr_engine_type})",
                        "character_count": len(ocr_text)
                    })
                    aggregated_text_blocks.append(f"--- Page {page_num} (OCR) ---\n{ocr_text}")
        elif is_image(content_type, filename):
            detected_format = "image"
            normalized_bytes, dims = normalize_image_bytes(file_bytes)
            ocr_text = self._run_ocr_on_bytes(normalized_bytes)
            aggregated_text_blocks.append(ocr_text)
            pages_summary.append({
                "page": 1,
                "type": f"image_ocr ({self.ocr_engine_type})",
                "dimensions": dims,
                "character_count": len(ocr_text)
            })
        else:
            detected_format = "fallback_raw"
            try:
                normalized_bytes, dims = normalize_image_bytes(file_bytes)
                ocr_text = self._run_ocr_on_bytes(normalized_bytes)
                aggregated_text_blocks.append(ocr_text)
                pages_summary.append({
                    "page": 1,
                    "type": f"image_ocr ({self.ocr_engine_type})",
                    "dimensions": dims,
                    "character_count": len(ocr_text)
                })
            except Exception:
                raw_str = file_bytes.decode("utf-8", errors="ignore")
                aggregated_text_blocks.append(raw_str)
                pages_summary.append({
                    "page": 1,
                    "type": "raw_utf8_decode",
                    "character_count": len(raw_str)
                })

        if trace:
            stages.append({
                "stage": 1,
                "name": "file_triage",
                "details": {
                    "filename": filename,
                    "content_type": content_type,
                    "file_size_bytes": len(file_bytes),
                    "detected_format": detected_format,
                    "pages": pages_summary
                }
            })

        full_extracted_text = "\n\n".join(aggregated_text_blocks).strip()

        if trace:
            stages.append({
                "stage": 2,
                "name": "raw_text_extraction",
                "details": {
                    "ocr_engine": self.ocr_engine_type if detected_format != "pdf" or any("ocr" in str(p.get("type")) for p in pages_summary) else "digital_pdf_stream",
                    "extracted_text": full_extracted_text,
                    "total_characters": len(full_extracted_text)
                }
            })

        if not full_extracted_text:
            raise ValueError("No readable text could be extracted from the document")

        # Stage 3: Prompt Construction
        system_prompt = document.build_system_prompt()
        user_prompt = document.build_user_prompt(full_extracted_text)
        json_schema = document.get_json_schema()

        if trace:
            stages.append({
                "stage": 3,
                "name": "prompt_construction",
                "details": {
                    "document_slug": document.slug,
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "target_json_schema": json_schema
                }
            })

        # Stage 4: LLM Structured Generation
        raw_json_dict = await self.llm_provider.generate_structured(
            prompt=user_prompt,
            json_schema=json_schema,
            system_prompt=system_prompt
        )

        if trace:
            stages.append({
                "stage": 4,
                "name": "llm_structured_output",
                "details": {
                    "provider": getattr(self.llm_provider, "name", "ollama"),
                    "model": getattr(self.llm_provider, "model", "unknown"),
                    "raw_llm_json": raw_json_dict
                }
            })

        # Stage 5: Schema Validation & Normalization
        validated_model = document.validate_payload(raw_json_dict)
        final_data = validated_model.model_dump()

        if trace:
            stages.append({
                "stage": 5,
                "name": "schema_validation",
                "details": {
                    "schema_class": document.schema_class.__name__,
                    "validated_fields": list(final_data.keys()),
                    "final_output": final_data
                }
            })

        trace_data = {"engine": self.name, "stages": stages} if trace else None
        return ExtractionResult(data=final_data, trace=trace_data)


# Backward compatibility alias
LocalCpuEngine = OcrHybridEngine
