import io
import logging
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image
from src.modules.base import ExtractionOutput
from src.modules.extractors.base import BaseTextExtractor
from src.modules.preprocessors.base import BaseImagePreprocessor
from src.utility.pdf_utils import is_pdf
from src.utility.usage_cost import OcrUsage, record_ocr_usage

logger = logging.getLogger(__name__)


class OcrExtractor(BaseTextExtractor):
    """
    Unified OCR Text Extractor supporting:
    - RapidOCR (ONNX CPU)
    - Tesseract OCR (via pytesseract)
    - Google Cloud Vision API OCR (supporting API key, Service Account, and Project ID / gcloud ADC)
    """

    def __init__(
        self,
        backend: str = "rapidocr",
        tesseract_cmd: Optional[str] = None,
        google_api_key: Optional[str] = None,
        google_project_id: Optional[str] = None,
        google_credentials: Optional[str] = None,
        preprocessor: Optional[BaseImagePreprocessor] = None,
    ) -> None:
        self.backend = (backend or "rapidocr").lower()
        self.name = f"ocr_{self.backend}"
        self.tesseract_cmd = tesseract_cmd
        self.google_api_key = google_api_key
        self.google_project_id = google_project_id
        self.google_credentials = google_credentials
        self.preprocessor = preprocessor
        self._rapid_ocr: Any = None
        self._vision_client: Any = None

        if self.tesseract_cmd:
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            except ImportError:
                pass

    def _get_rapid_ocr(self) -> Any:
        if self._rapid_ocr is None:
            try:
                from rapidocr_onnxruntime import RapidOCR  # type: ignore
                self._rapid_ocr = RapidOCR()
            except ImportError as err:
                logger.error("rapidocr-onnxruntime is not installed.")
                raise RuntimeError("rapidocr-onnxruntime is required for RapidOCR backend") from err
        return self._rapid_ocr

    def _get_google_vision_client(self) -> Any:
        if self._vision_client is None:
            try:
                import json
                import os
                from google.cloud import vision
                from google.api_core.client_options import ClientOptions
                from google.oauth2 import service_account
                import google.auth

                annotator_cls: Any = vision.ImageAnnotatorClient

                # 1. Service account JSON file
                if self.google_credentials:
                    self._vision_client = annotator_cls.from_service_account_json(self.google_credentials)

                # 2. API Key Client Option
                elif self.google_api_key:
                    client_options = ClientOptions(api_key=self.google_api_key)
                    self._vision_client = annotator_cls(client_options=client_options)

                # 3. Project ID / gcloud ADC (Application Default Credentials)
                elif self.google_project_id:
                    try:
                        credentials, _ = google.auth.default(quota_project_id=self.google_project_id)
                        client_options = ClientOptions(quota_project_id=self.google_project_id)
                        self._vision_client = annotator_cls(
                            credentials=credentials,
                            client_options=client_options
                        )
                    except Exception as auth_err:
                        logger.warning(
                            f"Google auth initialization with quota_project_id '{self.google_project_id}' "
                            f"fell back to default: {auth_err}"
                        )
                        self._vision_client = annotator_cls()

                # 4. Ambient gcloud ADC authentication
                else:
                    self._vision_client = annotator_cls()

            except ImportError as err:
                logger.error("google-cloud-vision package is not installed.")
                raise RuntimeError("google-cloud-vision is required for google_vision backend") from err
        return self._vision_client

    def _ocr_single_image(self, image_bytes: bytes) -> Tuple[str, float, Dict[str, Any]]:
        """Executes OCR on a single image and computes (text, confidence, meta)."""
        if self.preprocessor:
            prep_res = self.preprocessor.preprocess(image_bytes)
            image_bytes = prep_res.processed_bytes
            prep_meta = prep_res.metadata
        else:
            prep_meta = {}

        if self.backend == "tesseract":
            return self._ocr_tesseract(image_bytes, prep_meta)
        elif self.backend in ("google_vision", "google_cloud_vision", "cloud_vision"):
            return self._ocr_google_vision(image_bytes, prep_meta)
        else:
            return self._ocr_rapidocr(image_bytes, prep_meta)

    def _ocr_rapidocr(self, image_bytes: bytes, prep_meta: Dict[str, Any]) -> Tuple[str, float, Dict[str, Any]]:
        ocr = self._get_rapid_ocr()
        result, elapse = ocr(image_bytes)
        if not result:
            return "", 0.0, {"backend": "rapidocr", "preprocessing": prep_meta}

        extracted_lines: List[str] = []
        confidences: List[float] = []

        for item in result:
            if len(item) > 1 and item[1]:
                text = str(item[1]).strip()
                extracted_lines.append(text)
                if len(item) > 2 and item[2] is not None:
                    try:
                        confidences.append(float(item[2]))
                    except (ValueError, TypeError):
                        pass

        full_text = "\n".join(extracted_lines).strip()
        avg_confidence = (sum(confidences) / len(confidences)) if confidences else (0.8 if full_text else 0.0)
        avg_confidence = min(1.0, max(0.0, round(avg_confidence, 3)))

        return full_text, avg_confidence, {
            "backend": "rapidocr",
            "line_count": len(extracted_lines),
            "raw_confidence": avg_confidence,
            "preprocessing": prep_meta
        }

    def _ocr_tesseract(self, image_bytes: bytes, prep_meta: Dict[str, Any]) -> Tuple[str, float, Dict[str, Any]]:
        try:
            import pytesseract
            from pytesseract import Output
            if self.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

            with Image.open(io.BytesIO(image_bytes)) as img:
                data = pytesseract.image_to_data(img, output_type=Output.DICT)
                
            texts: List[str] = []
            confs: List[float] = []
            n_boxes = len(data.get("text", []))
            for i in range(n_boxes):
                w_text = data["text"][i].strip()
                w_conf = data["conf"][i]
                if w_text:
                    texts.append(w_text)
                    try:
                        c_val = float(w_conf)
                        if c_val >= 0:
                            confs.append(c_val / 100.0)
                    except (ValueError, TypeError):
                        pass

            full_text = " ".join(texts).strip()
            avg_confidence = (sum(confs) / len(confs)) if confs else (0.75 if full_text else 0.0)
            avg_confidence = min(1.0, max(0.0, round(avg_confidence, 3)))

            return full_text, avg_confidence, {
                "backend": "tesseract",
                "word_count": len(texts),
                "raw_confidence": avg_confidence,
                "preprocessing": prep_meta
            }
        except ImportError as err:
            logger.error("pytesseract is not installed.")
            raise RuntimeError("pytesseract is required when OCR_BACKEND=tesseract") from err

    def _ocr_google_vision(self, image_bytes: bytes, prep_meta: Dict[str, Any]) -> Tuple[str, float, Dict[str, Any]]:
        client = self._get_google_vision_client()
        from google.cloud import vision
        image = vision.Image(content=image_bytes)
        try:
            response = client.document_text_detection(image=image)
        except Exception:
            record_ocr_usage(OcrUsage("google_vision", "document_text_detection", None))
            raise
        
        if getattr(response, "error", None) and getattr(response.error, "message", None):
            record_ocr_usage(OcrUsage("google_vision", "document_text_detection", None))
            raise RuntimeError(f"Google Cloud Vision OCR error: {response.error.message}")
        record_ocr_usage(OcrUsage("google_vision", "document_text_detection", 1))

        full_text = response.full_text_annotation.text if getattr(response, "full_text_annotation", None) else ""
        full_text = str(full_text or "").strip()

        # Compute average block/page confidence if available
        confs: List[float] = []
        if getattr(response, "full_text_annotation", None) and getattr(response.full_text_annotation, "pages", None):
            for page in response.full_text_annotation.pages:
                if hasattr(page, "confidence") and page.confidence > 0:
                    confs.append(float(page.confidence))

        avg_confidence = (sum(confs) / len(confs)) if confs else (0.95 if full_text else 0.0)
        avg_confidence = min(1.0, max(0.0, round(avg_confidence, 3)))

        return full_text, avg_confidence, {
            "backend": "google_vision",
            "raw_confidence": avg_confidence,
            "preprocessing": prep_meta
        }

    async def extract_text(
        self,
        file_bytes: bytes,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        **kwargs: Any,
    ) -> ExtractionOutput:
        if is_pdf(content_type, filename) and self.preprocessor:
            # Multi-page PDF: render pages to images and OCR each
            rendered_pages = self.preprocessor.render_pdf_to_images(file_bytes)
            page_outputs: List[str] = []
            page_confs: List[float] = []
            page_metas: List[Dict[str, Any]] = []

            for idx, page_img_bytes in enumerate(rendered_pages, start=1):
                p_text, p_conf, p_meta = self._ocr_single_image(page_img_bytes)
                if p_text:
                    page_outputs.append(f"--- Page {idx} (OCR) ---\n{p_text}")
                page_confs.append(p_conf)
                page_metas.append({"page": idx, "confidence": p_conf, **p_meta})

            full_text = "\n\n".join(page_outputs).strip()
            total_conf = (sum(page_confs) / len(page_confs)) if page_confs else 0.0
            return ExtractionOutput(
                text=full_text,
                confidence=round(total_conf, 3),
                stage_name=self.name,
                metadata={"page_count": len(rendered_pages), "pages": page_metas}
            )

        # Single Image / Fallback
        text, conf, meta = self._ocr_single_image(file_bytes)
        return ExtractionOutput(
            text=text,
            confidence=conf,
            stage_name=self.name,
            metadata=meta
        )
