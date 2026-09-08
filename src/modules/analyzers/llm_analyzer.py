import logging
from typing import Any, Dict
from src.domain.base import BaseDocument
from src.modules.analyzers.base import BaseTextAnalyzer
from src.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class LlmTextAnalyzer(BaseTextAnalyzer):
    """
    Structured LLM Text Analyzer.
    Sends extracted raw text + JSON schema constraints to LLM provider (Ollama or Google Gemini).
    """

    name = "llm_analyzer"

    def __init__(self, llm_provider: BaseLLMProvider) -> None:
        self.llm_provider = llm_provider

    async def analyze(
        self,
        input_data: Any,
        document: BaseDocument,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        raw_text = str(input_data or "").strip()
        if not raw_text:
            raise ValueError("Empty text provided to LlmTextAnalyzer")

        system_prompt = document.build_system_prompt()
        user_prompt = document.build_user_prompt(raw_text)
        json_schema = document.get_json_schema()

        raw_json_dict = await self.llm_provider.generate_structured(
            prompt=user_prompt,
            json_schema=json_schema,
            system_prompt=system_prompt
        )

        validated_model = document.validate_payload(raw_json_dict)
        return validated_model.model_dump()
