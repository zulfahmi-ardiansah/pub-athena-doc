import logging
from typing import Any, Dict, List, Optional
from src.domain.base import BaseDocument
from src.engines.base import BaseExtractionEngine
from src.providers.base import BaseLLMProvider
from src.utility.pdf_utils import is_pdf, inspect_and_extract_pdf_pages
from src.utility.image_utils import is_image, normalize_image_bytes

logger = logging.getLogger(__name__)


class LocalCpuEngine(BaseExtractionEngine):
    """
    Local CPU extraction engine:
    1. Multi-page PDF / Image triage.
    2. Digital PDF text extraction (PyMuPDF) or RapidOCR (ONNX CPU).
    3. Structured JSON extraction via local LLM provider (Ollama Qwen 2.5).
    """

    name = "local_cpu"

    def __init__(self, llm_provider: BaseLLMProvider) -> None:
        self.llm_provider = llm_provider
        self._ocr_engine = None

    def _get_ocr(self):
        """Lazy-load RapidOCR ONNX instance."""
        if self._ocr_engine is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
                self._ocr_engine = RapidOCR()
            except ImportError as err:
                logger.error("rapidocr-onnxruntime is not installed.")
                raise RuntimeError("RapidOCR is required for LocalCpuEngine OCR processing") from err
        return self._ocr_engine

    def _run_ocr_on_bytes(self, image_bytes: bytes) -> str:
        """Executes RapidOCR on raw image bytes."""
        ocr = self._get_ocr()
        result, _ = ocr(image_bytes)
        if not result:
            return ""
        # result items: [box_points, text, confidence_score]
        return "\n".join(item[1] for item in result if len(item) > 1 and item[1])

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
