import io
import logging
from typing import Any, Dict, List, Optional
from PIL import Image
from src.domain.base import BaseDocument
from src.engines.base import BaseExtractionEngine
from src.providers.base import BaseLLMProvider
from src.utility.pdf_utils import is_pdf, inspect_and_extract_pdf_pages
from src.utility.image_utils import is_image, normalize_image_bytes

logger = logging.getLogger(__name__)


class OcrHybridEngine(BaseExtractionEngine):
    """
    OCR Hybrid extraction engine:
    1. Multi-page PDF / Image triage.
    2. Digital PDF text extraction (PyMuPDF) or OCR (RapidOCR ONNX / Tesseract).
    3. Structured JSON extraction via local/hybrid LLM provider (e.g. Ollama Qwen 2.5).
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
        """Preloads LLM model into memory so inferences don't incur model load delay."""
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
            # result items: [box_points, text, confidence_score]
            return "\n".join(item[1] for item in result if len(item) > 1 and item[1]).strip()

    async def extract(
        self,
        file_bytes: bytes,
        filename: Optional[str],
        content_type: Optional[str],
        document: BaseDocument
    ) -> Dict[str, Any]:
        aggregated_text_blocks: List[str] = []

        if is_pdf(content_type, filename):
            pages = inspect_and_extract_pdf_pages(file_bytes)
            for page_num, digital_text, rendered_png in pages:
                if digital_text:
                    aggregated_text_blocks.append(f"--- Page {page_num} ---\n{digital_text}")
                elif rendered_png:
                    ocr_text = self._run_ocr_on_bytes(rendered_png)
                    aggregated_text_blocks.append(f"--- Page {page_num} (OCR) ---\n{ocr_text}")
        elif is_image(content_type, filename):
            normalized_bytes, _ = normalize_image_bytes(file_bytes)
            ocr_text = self._run_ocr_on_bytes(normalized_bytes)
            aggregated_text_blocks.append(ocr_text)
        else:
            # Fallback: Attempt image normalization and OCR
            try:
                normalized_bytes, _ = normalize_image_bytes(file_bytes)
                ocr_text = self._run_ocr_on_bytes(normalized_bytes)
                aggregated_text_blocks.append(ocr_text)
            except Exception:
                # If image fails, attempt plain text decode
                raw_str = file_bytes.decode("utf-8", errors="ignore")
                aggregated_text_blocks.append(raw_str)

        full_extracted_text = "\n\n".join(aggregated_text_blocks).strip()

        if not full_extracted_text:
            raise ValueError("No readable text could be extracted from the document")

        system_prompt = document.build_system_prompt()
        user_prompt = document.build_user_prompt(full_extracted_text)
        json_schema = document.get_json_schema()

        raw_json_dict = await self.llm_provider.generate_structured(
            prompt=user_prompt,
            json_schema=json_schema,
            system_prompt=system_prompt
        )

        # Validate through domain schema class
        validated_model = document.validate_payload(raw_json_dict)
        return validated_model.model_dump()


# Backward compatibility alias
LocalCpuEngine = OcrHybridEngine
