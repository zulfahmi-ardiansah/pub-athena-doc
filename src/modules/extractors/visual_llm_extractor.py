import base64
import logging
from typing import Any, Dict, List, Optional
from src.modules.base import ExtractionOutput
from src.modules.extractors.base import BaseTextExtractor
from src.modules.preprocessors.base import BaseImagePreprocessor
from src.providers.base import BaseLLMProvider
from src.utility.pdf_utils import is_pdf

logger = logging.getLogger(__name__)

RAW_OCR_SYSTEM_PROMPT = (
    "You are an expert Optical Character Recognition (OCR) engine. "
    "Your task is to transcribe all printed and handwritten text from the image accurately and verbatim.\n"
    "- Maintain original reading order and line breaks.\n"
    "- Do not summarize, edit, translate, or explain.\n"
    "- Do not output JSON or Markdown conversational wrappers.\n"
    "- Return ONLY the exact transcribed text."
)

RAW_OCR_USER_PROMPT = "Transcribe all visible text from this image exactly as printed."


class VisualLlmExtractor(BaseTextExtractor):
    """
    Multimodal Vision LLM Text Extractor.
    Transcribes raw text from document images using Visual LLM (Ollama Vision or Google Gemini Vision).
    """

    name = "visual_llm"

    def __init__(
        self,
        vision_provider: BaseLLMProvider,
        preprocessor: Optional[BaseImagePreprocessor] = None,
    ) -> None:
        self.vision_provider = vision_provider
        self.preprocessor = preprocessor

    async def _extract_from_image_bytes(self, image_bytes: bytes) -> str:
        if self.preprocessor:
            prep_res = self.preprocessor.preprocess(image_bytes)
            image_bytes = prep_res.processed_bytes

        b64_img = base64.b64encode(image_bytes).decode("utf-8")
        result = await self.vision_provider.generate_text(
            prompt=RAW_OCR_USER_PROMPT,
            system_prompt=RAW_OCR_SYSTEM_PROMPT,
            images=[b64_img]
        )
        return str(result or "").strip()

    async def extract_text(
        self,
        file_bytes: bytes,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        **kwargs: Any,
    ) -> ExtractionOutput:
        if is_pdf(content_type, filename) and self.preprocessor:
            rendered_pages = self.preprocessor.render_pdf_to_images(file_bytes)
            page_outputs: List[str] = []
            for idx, page_bytes in enumerate(rendered_pages, start=1):
                text = await self._extract_from_image_bytes(page_bytes)
                if text and text.strip():
                    page_outputs.append(f"--- Page {idx} (Vision) ---\n{text.strip()}")

            full_text = "\n\n".join(page_outputs).strip()
            conf = 0.90 if full_text else 0.0
            return ExtractionOutput(
                text=full_text,
                confidence=conf,
                stage_name=self.name,
                metadata={"page_count": len(rendered_pages)}
            )

        # Single image
        text = await self._extract_from_image_bytes(file_bytes)
        text = text.strip() if text else ""
        conf = 0.90 if text else 0.0
        return ExtractionOutput(
            text=text,
            confidence=conf,
            stage_name=self.name,
            metadata={"character_count": len(text)}
        )
