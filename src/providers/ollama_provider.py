import json
import logging
from typing import Any, Dict
import httpx
from src.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """
    Ollama provider utilizing native JSON Schema constrained generation.
    Forces temperature=0.0 and greedy decoding for deterministic extraction.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:3b",
        timeout_seconds: float = 60.0
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout_seconds

    async def generate_structured(
        self,
        prompt: str,
        json_schema: Dict[str, Any],
        system_prompt: str = ""
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "format": json_schema,
            "stream": False,
            "options": {
                "temperature": 0.0,
                "top_p": 0.1,
                "seed": 42
            }
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
            except httpx.HTTPError as err:
                logger.error(f"Ollama request error: {err}")
                raise RuntimeError(f"Ollama inference failed: {err}") from err

        result_json = response.json()
        raw_response_text = result_json.get("response", "")

        try:
            parsed = json.loads(raw_response_text)
            if not isinstance(parsed, dict):
                raise ValueError("Ollama response is not a JSON object")
            return parsed
        except json.JSONDecodeError as err:
            logger.error(f"Failed to parse Ollama output as JSON: {raw_response_text}")
            raise ValueError(f"Ollama produced invalid JSON: {raw_response_text}") from err
