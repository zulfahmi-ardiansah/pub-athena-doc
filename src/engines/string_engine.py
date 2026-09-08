import logging
from typing import Any, Dict, List, Optional
from src.domain.base import BaseDocument
from src.engines.base import BaseExtractionEngine, ExtractionResult, ExtractionError
from src.modules.base import ExtractionOutput
from src.modules.extractors.base import BaseTextExtractor
from src.modules.extractors.digital_pdf import DigitalPdfExtractor
from src.modules.extractors.ocr_extractor import OcrExtractor
from src.modules.analyzers.string_analyzer import StringTextAnalyzer
from src.modules.preprocessors.base import BaseImagePreprocessor
from src.utility.pdf_utils import is_pdf

logger = logging.getLogger(__name__)


class StringEngine(BaseExtractionEngine):
    """
    Zero-LLM Fast Extraction Engine:
    1. Extracts text via Digital PDF stream, falling back to OCR if confidence is low.
    2. Executes deterministic String Text Analysis (Regex / Heuristics) on the extracted text.
    """

    name = "string_engine"

    def __init__(
        self,
        digital_extractor: Optional[BaseTextExtractor] = None,
        ocr_extractor: Optional[BaseTextExtractor] = None,
        analyzer: Optional[StringTextAnalyzer] = None,
        preprocessor: Optional[BaseImagePreprocessor] = None,
        min_confidence: float = 0.5,
    ) -> None:
        self.digital_extractor = digital_extractor or DigitalPdfExtractor()
        self.ocr_extractor = ocr_extractor or OcrExtractor(preprocessor=preprocessor)
        self.analyzer = analyzer or StringTextAnalyzer()
        self.preprocessor = preprocessor
        self.min_confidence = min_confidence

    async def warmup(self) -> None:
        # String engine has no heavy neural LLMs to preload
        pass

    async def extract(
        self,
        file_bytes: bytes,
        filename: Optional[str],
        content_type: Optional[str],
        document: BaseDocument,
        trace: bool = False,
    ) -> ExtractionResult:
        stages: List[Dict[str, Any]] = []

        if not file_bytes:
            err_msg = "Empty file provided for extraction"
            if trace:
                stages.append({"stage": 1, "name": "file_check", "status": "failed", "details": {"error": err_msg}})
            raise ExtractionError(message=err_msg, trace={"engine": self.name, "stages": stages} if trace else None)

        # Stage 1: Text Extraction (Digital PDF with OCR fallback)
        extraction_output: Optional[ExtractionOutput] = None
        is_pdf_file = is_pdf(content_type, filename)

        if is_pdf_file:
            try:
                extraction_output = await self.digital_extractor.extract_text(
                    file_bytes=file_bytes,
                    filename=filename,
                    content_type=content_type
                )
            except Exception as exc:
                logger.warning(f"Digital PDF extraction failed, falling back to OCR: {exc}")

        # Fallback to OCR if not PDF or low confidence
        if (
            not extraction_output
            or extraction_output.is_empty
            or extraction_output.confidence < self.min_confidence
        ):
            fallback_reason = (
                "file is not digital pdf" if not is_pdf_file
                else f"confidence ({getattr(extraction_output, 'confidence', 0.0)}) < threshold ({self.min_confidence})"
            )
            try:
                ocr_output = await self.ocr_extractor.extract_text(
                    file_bytes=file_bytes,
                    filename=filename,
                    content_type=content_type
                )
                extraction_output = ocr_output
            except Exception as exc:
                if trace:
                    stages.append({
                        "stage": 1,
                        "name": "ocr_fallback",
                        "status": "failed",
                        "details": {"error": str(exc), "fallback_reason": fallback_reason}
                    })
                raise ExtractionError(
                    message=f"OCR extraction failed: {exc}",
                    trace={"engine": self.name, "stages": stages} if trace else None
                ) from exc

        if trace:
            stages.append({
                "stage": 1,
                "name": "text_extraction",
                "status": "completed" if not extraction_output.is_empty else "failed",
                "details": {
                    "stage_used": extraction_output.stage_name,
                    "confidence": extraction_output.confidence,
                    "text_length": len(extraction_output.text),
                    "extracted_text": extraction_output.text,
                    "metadata": extraction_output.metadata
                }
            })

        if extraction_output.is_empty:
            err_msg = "No readable text could be extracted from the document"
            raise ExtractionError(
                message=err_msg,
                trace={"engine": self.name, "stages": stages} if trace else None
            )

        # Stage 2: String Text Analysis
        try:
            analyzed_data = await self.analyzer.analyze(
                input_data=extraction_output.text,
                document=document
            )
        except Exception as exc:
            if trace:
                stages.append({
                    "stage": 2,
                    "name": "string_analysis",
                    "status": "failed",
                    "details": {"error": str(exc), "error_type": exc.__class__.__name__}
                })
            raise ExtractionError(
                message=f"String text analysis failed: {exc}",
                trace={"engine": self.name, "stages": stages} if trace else None
            ) from exc

        if trace:
            stages.append({
                "stage": 2,
                "name": "string_analysis",
                "status": "completed",
                "details": {
                    "document_slug": document.slug,
                    "extracted_fields": list(analyzed_data.keys()),
                    "final_output": analyzed_data
                }
            })

        trace_data = {"engine": self.name, "stages": stages} if trace else None
        return ExtractionResult(data=analyzed_data, trace=trace_data)
