import logging
from typing import Any, Dict, List, Mapping, Optional, Union
from src.domain.base import BaseDocument
from src.engines.base import BaseExtractionEngine, ExtractionResult, ExtractionError
from src.modules.base import ExtractionOutput
from src.modules.extractors.base import BaseTextExtractor
from src.modules.analyzers.base import BaseTextAnalyzer
from src.modules.preprocessors.base import BaseImagePreprocessor
from src.utility.pdf_utils import is_pdf
from src.config.telemetry import async_trace_span

logger = logging.getLogger(__name__)


class HybridEngine(BaseExtractionEngine):
    """
    Configurable Hybrid Extraction Engine:
    1. Configurable extraction priority pipeline (e.g. Digital PDF -> OCR -> Visual LLM).
    2. Sequentially evaluates confidence and automatically cascades to the next extractor when confidence is low.
    3. Configurable analysis mode (LLM structured generation or deterministic String parsing).
    """

    name = "hybrid_engine"

    def __init__(
        self,
        extractors: Mapping[str, BaseTextExtractor],
        analyzers: Mapping[str, BaseTextAnalyzer],
        preprocessor: Optional[BaseImagePreprocessor] = None,
        pipeline: Optional[List[str]] = None,
        min_confidence: float = 0.5,
        analysis_mode: str = "text_llm",
    ) -> None:
        self.extractors = dict(extractors)
        self.analyzers = dict(analyzers)
        self.preprocessor = preprocessor
        self.pipeline = pipeline or ["digital_pdf", "ocr", "visual_llm"]
        self.min_confidence = min_confidence
        mode = (analysis_mode or "text_llm").lower()
        self.analysis_mode = "text_llm" if mode == "llm" else mode

    async def warmup(self) -> None:
        for extractor in self.extractors.values():
            if hasattr(extractor, "vision_provider") and hasattr(extractor.vision_provider, "preload"):
                await extractor.vision_provider.preload()
        for analyzer in self.analyzers.values():
            if hasattr(analyzer, "llm_provider") and hasattr(analyzer.llm_provider, "preload"):
                await analyzer.llm_provider.preload()
            elif hasattr(analyzer, "vision_provider") and hasattr(analyzer.vision_provider, "preload"):
                await analyzer.vision_provider.preload()

    async def extract(
        self,
        file_bytes: bytes,
        filename: Optional[str],
        content_type: Optional[str],
        document: BaseDocument,
        trace: bool = False,
        pipeline_override: Optional[List[str]] = None,
        analysis_mode_override: Optional[str] = None,
    ) -> ExtractionResult:
        stages: List[Dict[str, Any]] = []

        if not file_bytes:
            err_msg = "Empty file provided for extraction"
            if trace:
                stages.append({"stage": 1, "name": "file_check", "status": "failed", "details": {"error": err_msg}})
            raise ExtractionError(message=err_msg, trace={"engine": self.name, "stages": stages} if trace else None)

        active_pipeline = pipeline_override or self.pipeline
        active_analysis_mode = (analysis_mode_override or self.analysis_mode).lower()
        is_pdf_file = is_pdf(content_type, filename)

        best_output: Optional[ExtractionOutput] = None
        attempted_stages: List[Dict[str, Any]] = []

        # Stage 1: Extraction Cascade
        async with async_trace_span("pipeline.extraction_cascade", {"pipeline": str(active_pipeline)}):
            for stage_name in active_pipeline:
                stage_key = stage_name.strip().lower()
                extractor = self.extractors.get(stage_key)
                if not extractor:
                    logger.warning(f"Extractor '{stage_key}' not found in registered extractors, skipping.")
                    continue

                # Skip digital PDF extractor for image files
                if stage_key == "digital_pdf" and not is_pdf_file:
                    continue

                try:
                    async with async_trace_span(f"extractor.{stage_key}"):
                        out = await extractor.extract_text(
                            file_bytes=file_bytes,
                            filename=filename,
                            content_type=content_type
                        )
                    attempted_stages.append({
                        "stage": stage_key,
                        "confidence": out.confidence,
                        "text_length": len(out.text),
                        "accepted": not out.is_empty and out.confidence >= self.min_confidence,
                        "metadata": out.metadata
                    })

                    if not out.is_empty and out.confidence >= self.min_confidence:
                        best_output = out
                        break

                    if not out.is_empty and (best_output is None or out.confidence > best_output.confidence):
                        best_output = out

                except Exception as exc:
                    logger.warning(f"Extractor '{stage_key}' execution failed: {exc}")
                    attempted_stages.append({
                        "stage": stage_key,
                        "status": "error",
                        "error": str(exc)
                    })

        if trace:
            stages.append({
                "stage": 1,
                "name": "extraction_pipeline",
                "status": "completed" if best_output and not best_output.is_empty else "failed",
                "details": {
                    "pipeline": active_pipeline,
                    "min_confidence_threshold": self.min_confidence,
                    "selected_stage": best_output.stage_name if best_output else None,
                    "selected_confidence": best_output.confidence if best_output else 0.0,
                    "extracted_text": best_output.text if best_output else "",
                    "attempts": attempted_stages
                }
            })

        if not best_output or best_output.is_empty:
            err_msg = "No readable text could be extracted by any extractor in the pipeline"
            raise ExtractionError(
                message=err_msg,
                trace={"engine": self.name, "stages": stages} if trace else None
            )

        # Stage 2: Text Analysis
        if active_analysis_mode == "llm":
            active_analysis_mode = "text_llm"

        analyzer = self.analyzers.get(active_analysis_mode)
        if not analyzer:
            fallback_mode = "string" if active_analysis_mode == "text_llm" else "text_llm"
            analyzer = self.analyzers.get(fallback_mode)
            if not analyzer:
                raise RuntimeError(f"No analyzer available for analysis_mode '{active_analysis_mode}'")
            logger.warning(f"Analyzer '{active_analysis_mode}' not found, falling back to '{fallback_mode}'")
            active_analysis_mode = fallback_mode

        try:
            async with async_trace_span(f"analyzer.{active_analysis_mode}", {"document.slug": document.slug}):
                analyzed_data = await analyzer.analyze(
                    input_data=best_output.text,
                    document=document
                )
        except Exception as exc:
            if trace:
                stages.append({
                    "stage": 2,
                    "name": "text_analysis",
                    "status": "failed",
                    "details": {
                        "analysis_mode": active_analysis_mode,
                        "error": str(exc),
                        "error_type": exc.__class__.__name__
                    }
                })
            raise ExtractionError(
                message=f"Text analysis ({active_analysis_mode}) failed: {exc}",
                trace={"engine": self.name, "stages": stages} if trace else None
            ) from exc

        if trace:
            stages.append({
                "stage": 2,
                "name": "text_analysis",
                "status": "completed",
                "details": {
                    "analysis_mode": active_analysis_mode,
                    "document_slug": document.slug,
                    "extracted_fields": list(analyzed_data.keys()),
                    "final_output": analyzed_data
                }
            })

        trace_data = {"engine": self.name, "stages": stages} if trace else None
        return ExtractionResult(data=analyzed_data, trace=trace_data)
