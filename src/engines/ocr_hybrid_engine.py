import base64
import io
import logging
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image
from src.domain.base import BaseDocument
from src.engines.base import BaseExtractionEngine, ExtractionResult, ExtractionError
from src.providers.base import BaseLLMProvider
from src.utility.pdf_utils import is_pdf, inspect_and_extract_pdf_pages
from src.utility.image_utils import is_image, normalize_image_bytes, preprocess_image_bytes

logger = logging.getLogger(__name__)


class OcrHybridEngine(BaseExtractionEngine):
    """
    OCR Hybrid extraction engine:
    1. Multi-page PDF / Image triage.
    2. Image preprocessing: deskewing, CLAHE contrast enhancement, thresholding.
    3. Digital PDF text extraction (PyMuPDF) or OCR (RapidOCR ONNX / Tesseract / Vision Model).
    4. Structured JSON extraction via local LLM provider (Ollama Qwen 2.5).
    """

    name = "ocr_hybrid"

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        vision_provider: Optional[BaseLLMProvider] = None,
        ocr_engine_type: str = "rapidocr",
        tesseract_cmd: Optional[str] = None,
        preprocess: bool = True,
        deskew: bool = True,
        enhance_contrast: bool = True,
        threshold_mode: Optional[str] = "none",
        gamma: float = 1.15,
        white_cutoff: int = 230,
        black_level: int = 25
    ) -> None:
        self.llm_provider = llm_provider
        self.vision_provider = vision_provider
        self.ocr_engine_type = (ocr_engine_type or "rapidocr").lower()
        self.tesseract_cmd = tesseract_cmd
        self.preprocess = preprocess
        self.deskew = deskew
        self.enhance_contrast = enhance_contrast
        self.threshold_mode = threshold_mode or "none"
        self.gamma = gamma
        self.white_cutoff = white_cutoff
        self.black_level = black_level
        self._rapid_ocr = None

        if self.tesseract_cmd:
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            except ImportError:
                pass

    async def warmup(self) -> None:
        """Preloads LLM model(s) into memory."""
        if hasattr(self.llm_provider, "preload"):
            await self.llm_provider.preload()
        if self.ocr_engine_type in ("vision_model", "visual_model", "vision") and self.vision_provider:
            if hasattr(self.vision_provider, "preload"):
                await self.vision_provider.preload()

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

    def _run_ocr_on_bytes(self, image_bytes: bytes, apply_preprocessing: bool = True) -> str:
        """Executes selected OCR engine (RapidOCR or Tesseract) on raw or preprocessed image bytes."""
        if apply_preprocessing and self.preprocess:
            image_bytes, _ = self._preprocess_image(image_bytes)

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

    async def _run_vision_ocr(self, image_bytes: bytes) -> str:
        """Executes Vision Model to transcribe visible text from preprocessed image bytes."""
        if not self.vision_provider:
            raise RuntimeError(
                "vision_provider is required for OcrHybridEngine when ocr_engine is 'vision_model'"
            )
        b64_img = base64.b64encode(image_bytes).decode("utf-8")
        system_prompt = (
            "You are an expert optical character recognition (OCR) engine. "
            "Transcribe all printed and handwritten text from the image accurately and verbatim, "
            "preserving line breaks and reading order. Do not format as JSON or provide conversational markdown."
        )
        user_prompt = "Transcribe all visible text from this image exactly as printed."
        return await self.vision_provider.generate_text(
            prompt=user_prompt,
            system_prompt=system_prompt,
            images=[b64_img]
        )

    async def _extract_ocr_text(self, image_bytes: bytes) -> str:
        """Runs the appropriate OCR pipeline (Vision Model, Tesseract, or RapidOCR) on preprocessed image bytes."""
        if self.ocr_engine_type in ("vision_model", "visual_model", "vision"):
            return await self._run_vision_ocr(image_bytes)
        return self._run_ocr_on_bytes(image_bytes, apply_preprocessing=False)

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

        try:
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
                        processed_bytes, prep_meta = self._preprocess_image(rendered_png)
                        ocr_text = await self._extract_ocr_text(processed_bytes)
                        pages_summary.append({
                            "page": page_num,
                            "type": f"scanned_image_ocr ({self.ocr_engine_type})",
                            "character_count": len(ocr_text),
                            "preprocessing": prep_meta
                        })
                        aggregated_text_blocks.append(f"--- Page {page_num} (OCR) ---\n{ocr_text}")
            elif is_image(content_type, filename):
                detected_format = "image"
                normalized_bytes, dims = normalize_image_bytes(file_bytes)
                processed_bytes, prep_meta = self._preprocess_image(normalized_bytes)
                ocr_text = await self._extract_ocr_text(processed_bytes)
                aggregated_text_blocks.append(ocr_text)
                pages_summary.append({
                    "page": 1,
                    "type": f"image_ocr ({self.ocr_engine_type})",
                    "dimensions": dims,
                    "character_count": len(ocr_text),
                    "preprocessing": prep_meta
                })
            else:
                detected_format = "fallback_raw"
                try:
                    normalized_bytes, dims = normalize_image_bytes(file_bytes)
                    processed_bytes, prep_meta = self._preprocess_image(normalized_bytes)
                    ocr_text = await self._extract_ocr_text(processed_bytes)
                    aggregated_text_blocks.append(ocr_text)
                    pages_summary.append({
                        "page": 1,
                        "type": f"image_ocr ({self.ocr_engine_type})",
                        "dimensions": dims,
                        "character_count": len(ocr_text),
                        "preprocessing": prep_meta
                    })
                except Exception:
                    raw_str = file_bytes.decode("utf-8", errors="ignore")
                    aggregated_text_blocks.append(raw_str)
                    pages_summary.append({
                        "page": 1,
                        "type": "raw_utf8_decode",
                        "character_count": len(raw_str)
                    })
        except Exception as exc:
            if trace:
                stages.append({
                    "stage": 1,
                    "name": "file_triage",
                    "status": "failed",
                    "details": {
                        "filename": filename,
                        "content_type": content_type,
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
                "name": "file_triage",
                "status": "completed",
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
                "status": "completed" if full_extracted_text else "failed",
                "details": {
                    "ocr_engine": self.ocr_engine_type if detected_format != "pdf" or any("ocr" in str(p.get("type")) for p in pages_summary) else "digital_pdf_stream",
                    "extracted_text": full_extracted_text,
                    "total_characters": len(full_extracted_text)
                }
            })

        if not full_extracted_text:
            err_msg = "No readable text could be extracted from the document"
            raise ExtractionError(
                message=err_msg,
                trace={"engine": self.name, "stages": stages} if trace else None
            )

        # Stage 3: Prompt Construction
        system_prompt = document.build_system_prompt()
        user_prompt = document.build_user_prompt(full_extracted_text)
        json_schema = document.get_json_schema()

        if trace:
            stages.append({
                "stage": 3,
                "name": "prompt_construction",
                "status": "completed",
                "details": {
                    "document_slug": document.slug,
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "target_json_schema": json_schema
                }
            })

        # Stage 4: LLM Structured Generation
        try:
            raw_json_dict = await self.llm_provider.generate_structured(
                prompt=user_prompt,
                json_schema=json_schema,
                system_prompt=system_prompt
            )
        except Exception as exc:
            if trace:
                stages.append({
                    "stage": 4,
                    "name": "llm_structured_output",
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
                "stage": 4,
                "name": "llm_structured_output",
                "status": "completed",
                "details": {
                    "provider": getattr(self.llm_provider, "name", "ollama"),
                    "model": getattr(self.llm_provider, "model", "unknown"),
                    "raw_llm_json": raw_json_dict
                }
            })

        # Stage 5: Schema Validation & Normalization
        try:
            validated_model = document.validate_payload(raw_json_dict)
            final_data = validated_model.model_dump()
        except Exception as exc:
            if trace:
                stages.append({
                    "stage": 5,
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
                "stage": 5,
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


# Backward compatibility alias
LocalCpuEngine = OcrHybridEngine
