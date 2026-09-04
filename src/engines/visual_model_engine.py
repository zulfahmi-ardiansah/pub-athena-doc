import base64
import logging
from typing import Any, Dict, List, Optional
import fitz  # PyMuPDF
from src.domain.base import BaseDocument
from src.engines.base import BaseExtractionEngine
from src.providers.base import BaseLLMProvider
from src.utility.pdf_utils import is_pdf
from src.utility.image_utils import is_image, normalize_image_bytes

logger = logging.getLogger(__name__)


class VisualModelEngine(BaseExtractionEngine):
    """
    Pure Visual Model extraction engine:
    1. Multi-page PDF to rendered high-res image pages / Image normalization.
    2. Sends document image bytes directly to Ollama vision models (e.g. llama3.2-vision, qwen2.5-vl, minicpm-v).
    3. Structured JSON extraction constrained by JSON Schema natively on Ollama.
    """

    name = "visual_model"

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        render_dpi: int = 150
    ) -> None:
        self.llm_provider = llm_provider
        self.render_dpi = render_dpi

    async def warmup(self) -> None:
        """Preloads Vision LLM model into memory."""
        if hasattr(self.llm_provider, "preload"):
            await self.llm_provider.preload()

    def _render_pdf_to_images(self, pdf_bytes: bytes) -> List[bytes]:
        """Renders every page of a PDF into high-res PNG image bytes."""
        image_list: List[bytes] = []
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            zoom = self.render_dpi / 72.0
            matrix = fitz.Matrix(zoom, zoom)
            for page in doc:
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                image_list.append(pix.tobytes("png"))
        finally:
            doc.close()
        return image_list

    async def extract(
        self,
        file_bytes: bytes,
        filename: Optional[str],
        content_type: Optional[str],
        document: BaseDocument
    ) -> Dict[str, Any]:
        if not file_bytes:
            raise ValueError("Empty file provided for extraction")

        image_bytes_list: List[bytes] = []

        if is_pdf(content_type, filename):
            image_bytes_list = self._render_pdf_to_images(file_bytes)
        elif is_image(content_type, filename):
            norm_bytes, _ = normalize_image_bytes(file_bytes)
            image_bytes_list.append(norm_bytes)
        else:
            # Fallback: Attempt image normalization or pass raw bytes
            try:
                norm_bytes, _ = normalize_image_bytes(file_bytes)
                image_bytes_list.append(norm_bytes)
            except Exception:
                image_bytes_list.append(file_bytes)

        if not image_bytes_list:
            raise ValueError("Could not extract or render visual content from document")

        # Encode image list to base64 strings
        base64_images = [
            base64.b64encode(img_bytes).decode("utf-8")
            for img_bytes in image_bytes_list
        ]

        system_prompt = document.build_system_prompt()
        user_prompt = (
            f"Analyze the attached document image(s) for '{document.name}' ({document.description}) "
            "and extract all relevant structured fields into the JSON schema."
        )
        json_schema = document.get_json_schema()

        raw_json_dict = await self.llm_provider.generate_structured(
            prompt=user_prompt,
            json_schema=json_schema,
            system_prompt=system_prompt,
            images=base64_images
        )

        # Validate through domain schema class
        validated_model = document.validate_payload(raw_json_dict)
        return validated_model.model_dump()
