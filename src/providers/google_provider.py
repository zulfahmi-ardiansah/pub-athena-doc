import json
import logging
from typing import Any, Dict
from src.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class GoogleGenAIProvider(BaseLLMProvider):
    """
    Google Gemini cloud provider using structured response schema.
    """

    def __init__(
        self,
        api_key: str = "",
        model: str = "gemini-1.5-flash"
    ) -> None:
        self.api_key = api_key
        self.model = model
        self._client = None
        if api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=api_key)
            except ImportError:
                logger.warning("google-genai package not installed or failed to load.")

    async def generate_structured(
        self,
        prompt: str,
        json_schema: Dict[str, Any],
        system_prompt: str = ""
    ) -> Dict[str, Any]:
        if not self._client:
            raise RuntimeError("Google Gemini API client is not configured (missing GEMINI_API_KEY).")

        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=json_schema,
            temperature=0.0
        )

        response = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config
        )

        if not response.text:
            raise RuntimeError("Gemini returned empty response text")

        return json.loads(response.text)
