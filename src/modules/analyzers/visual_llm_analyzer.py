import base64
import logging
from typing import Any, Dict, List, Union
from src.domain.base import BaseDocument
from src.modules.analyzers.base import BaseTextAnalyzer
from src.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class VisualLlmAnalyzer(BaseTextAnalyzer):
    """
    Direct Multimodal Visual LLM Analyzer.
    Sends document image pages directly to multimodal Vision LLM (Ollama Vision or Google Gemini)
    with JSON Schema constraints.
    """

    name = "visual_llm_analyzer"

    def __init__(self, vision_provider: BaseLLMProvider) -> None:
        self.vision_provider = vision_provider

    async def analyze(
        self,
        input_data: Union[bytes, List[bytes], List[str]],
        document: BaseDocument,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        images_b64: List[str] = []

        if isinstance(input_data, bytes):
            images_b64.append(base64.b64encode(input_data).decode("utf-8"))
        elif isinstance(input_data, list):
            for item in input_data:
                if isinstance(item, bytes):
                    images_b64.append(base64.b64encode(item).decode("utf-8"))
                elif isinstance(item, str):
                    images_b64.append(item)

        if not images_b64:
            raise ValueError("No valid image data provided to VisualLlmAnalyzer")

        system_prompt = document.build_system_prompt()
        user_prompt = f"Extract all information for {document.name} from the document image(s) into the exact JSON schema."
        json_schema = document.get_json_schema()

        raw_json_dict = await self.vision_provider.generate_structured(
            prompt=user_prompt,
            json_schema=json_schema,
            system_prompt=system_prompt,
            images=images_b64
        )

        validated_model = document.validate_payload(raw_json_dict)
        return validated_model.model_dump()
