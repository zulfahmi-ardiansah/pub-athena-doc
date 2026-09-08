import logging
from typing import Any, Dict, List, Optional
from src.domain.base import BaseDocument
from src.engines.base import BaseExtractionEngine, ExtractionResult, ExtractionError
from src.modules.analyzers.visual_llm_analyzer import VisualLlmAnalyzer
from src.modules.preprocessors.base import BaseImagePreprocessor
from src.modules.preprocessors.image_preprocessor import ImagePreprocessor
from src.utility.pdf_utils import is_pdf

logger = logging.getLogger(__name__)


class VisualEngine(BaseExtractionEngine):
    """
    Direct Multimodal Visual Engine:
    Renders input document pages to high-res images and executes structured extraction
    directly via multimodal Vision LLM (Ollama or Google Gemini).
    """

    name = "visual_engine"

    def __init__(
        self,
        analyzer: VisualLlmAnalyzer,
        preprocessor: Optional[BaseImagePreprocessor] = None,
    ) -> None:
        self.analyzer = analyzer
        self.preprocessor = preprocessor or ImagePreprocessor()

    async def warmup(self) -> None:
        if hasattr(self.analyzer.vision_provider, "preload"):
            await self.analyzer.vision_provider.preload()

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

        # Stage 1: Page Rendering & Preprocessing
        image_bytes_list: List[bytes] = []
        try:
            if is_pdf(content_type, filename):
                raw_rendered = self.preprocessor.render_pdf_to_images(file_bytes)
                for page_bytes in raw_rendered:
                    prep_res = self.preprocessor.preprocess(page_bytes)
                    image_bytes_list.append(prep_res.processed_bytes)
            else:
                norm_bytes, _ = self.preprocessor.normalize_image(file_bytes)
                prep_res = self.preprocessor.preprocess(norm_bytes)
                image_bytes_list.append(prep_res.processed_bytes)
        except Exception as exc:
            if trace:
                stages.append({
                    "stage": 1,
                    "name": "image_preprocessing",
                    "status": "failed",
                    "details": {"error": str(exc)}
                })
            raise ExtractionError(
                message=f"Image preprocessing failed: {exc}",
                trace={"engine": self.name, "stages": stages} if trace else None
            ) from exc

        if trace:
            stages.append({
                "stage": 1,
                "name": "image_preprocessing",
                "status": "completed",
                "details": {
                    "page_count": len(image_bytes_list),
                    "filename": filename,
                    "content_type": content_type
                }
            })

        # Stage 2: Direct Visual-LLM Multimodal Analysis
        try:
            analyzed_data = await self.analyzer.analyze(
                input_data=image_bytes_list,
                document=document
            )
        except Exception as exc:
            if trace:
                stages.append({
                    "stage": 2,
                    "name": "visual_llm_analysis",
                    "status": "failed",
                    "details": {"error": str(exc), "error_type": exc.__class__.__name__}
                })
            raise ExtractionError(
                message=f"Visual LLM analysis failed: {exc}",
                trace={"engine": self.name, "stages": stages} if trace else None
            ) from exc

        if trace:
            stages.append({
                "stage": 2,
                "name": "visual_llm_analysis",
                "status": "completed",
                "details": {
                    "document_slug": document.slug,
                    "final_output": analyzed_data
                }
            })

        trace_data = {"engine": self.name, "stages": stages} if trace else None
        return ExtractionResult(data=analyzed_data, trace=trace_data)
