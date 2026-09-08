import logging
from typing import Any, Dict, List, Optional
import fitz  # PyMuPDF
from src.modules.base import ExtractionOutput
from src.modules.extractors.base import BaseTextExtractor

logger = logging.getLogger(__name__)


class DigitalPdfExtractor(BaseTextExtractor):
    """
    Fast direct text extractor for digital vector PDFs using PyMuPDF.
    Calculates confidence based on extracted text length, density, and printable character distribution.
    """

    name = "digital_pdf"

    def __init__(self, min_char_threshold: int = 25) -> None:
        self.min_char_threshold = min_char_threshold

    def _compute_confidence(self, text: str, page_count: int) -> float:
        cleaned = text.strip()
        char_count = len(cleaned)
        if char_count == 0:
            return 0.0

        if char_count < self.min_char_threshold:
            return round(char_count / (self.min_char_threshold * 2.0), 3)

        # Check ratio of alphanumeric characters
        alnum_count = sum(1 for c in cleaned if c.isalnum())
        alnum_ratio = alnum_count / char_count if char_count > 0 else 0.0

        # Base confidence for digital text with healthy length & alphanumeric ratio
        confidence = 0.85 + min(0.15, (char_count / (page_count * 200.0)) * 0.15)
        if alnum_ratio < 0.4:
            confidence *= 0.5

        return min(1.0, max(0.0, round(confidence, 3)))

    async def extract_text(
        self,
        file_bytes: bytes,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        **kwargs: Any,
    ) -> ExtractionOutput:
        page_texts: List[str] = []
        page_details: List[Dict[str, Any]] = []

        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            page_count = len(doc)
            try:
                for idx, page in enumerate(doc, start=1):
                    raw_text = page.get_text("text")
                    txt = raw_text.strip() if isinstance(raw_text, str) else str(raw_text or "").strip()
                    if txt:
                        page_texts.append(f"--- Page {idx} ---\n{txt}")
                    page_details.append({
                        "page": idx,
                        "character_count": len(txt),
                        "has_text": bool(txt)
                    })
            finally:
                doc.close()
        except Exception as exc:
            logger.debug(f"Digital PDF extraction skipped/failed: {exc}")
            return ExtractionOutput(
                text="",
                confidence=0.0,
                stage_name=self.name,
                metadata={"error": str(exc), "page_count": 0}
            )

        full_text = "\n\n".join(page_texts).strip()
        confidence = self._compute_confidence(full_text, page_count=page_count or 1)

        return ExtractionOutput(
            text=full_text,
            confidence=confidence,
            stage_name=self.name,
            metadata={
                "page_count": page_count,
                "character_count": len(full_text),
                "pages": page_details
            }
        )
