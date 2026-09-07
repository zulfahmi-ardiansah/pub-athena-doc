import json
import logging
from typing import Any, Dict, List, Optional
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
        timeout_seconds: float = 60.0,
        keep_alive: Any = -1,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout_seconds
        self.keep_alive = self._format_keep_alive(keep_alive)

    @staticmethod
    def _format_keep_alive(val: Any) -> Any:
        if val is None:
            return -1
        if isinstance(val, int):
            return val
        val_str = str(val).strip()
        if val_str.lstrip("-").isdigit():
            return int(val_str)
        return val_str

    async def preload(self) -> bool:
        """
        Preload the model into memory (RAM/VRAM) so first inference is instantaneous.
        """
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "keep_alive": self.keep_alive,
        }
        try:
            logger.info(f"Preloading Ollama model '{self.model}' (keep_alive={self.keep_alive})...")
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
            logger.info(f"Ollama model '{self.model}' is preloaded and ready in memory.")
            return True
        except Exception as err:
            logger.warning(
                f"Failed to preload Ollama model '{self.model}' at {self.base_url}: {err}. "
                "Inference will load model on-demand when requested."
            )
            return False

    async def generate_structured(
        self,
        prompt: str,
        json_schema: Dict[str, Any],
        system_prompt: str = "",
        images: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/generate"
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "format": json_schema,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": 0.0,
                "top_p": 0.1,
                "seed": 42,
                "num_ctx": 4096
            }
        }
        if images:
            payload["images"] = images

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
            return self._parse_json_payload(raw_response_text)
        except Exception as err:
            logger.error(f"Failed to parse Ollama output as JSON: {raw_response_text}")
            raise ValueError(f"Ollama produced invalid JSON: {raw_response_text}") from err

    @staticmethod
    def _parse_json_payload(text: str) -> Dict[str, Any]:
        """
        Parses JSON from model response, handling direct JSON, markdown code fences,
        and surrounding text preamble/postscript if present.
        """
        cleaned = text.strip() if text else ""
        if not cleaned:
            raise ValueError("Empty response received from Ollama")

        # 1. Direct parse attempt
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # 2. Strip markdown code fences (```json ... ``` or ``` ... ```)
        if "```" in cleaned:
            lines = cleaned.splitlines()
            code_lines = []
            inside_fence = False
            for line in lines:
                if line.strip().startswith("```"):
                    inside_fence = not inside_fence
                    continue
                if inside_fence:
                    code_lines.append(line)
            if code_lines:
                candidate = "\n".join(code_lines).strip()
                try:
                    parsed = json.loads(candidate)
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    pass

        # 3. Substring extraction: find outermost '{' and '}'
        first_brace = cleaned.find("{")
        last_brace = cleaned.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            candidate = cleaned[first_brace:last_brace + 1]
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

        raise ValueError("Response is not a valid JSON object")
