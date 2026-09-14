import json
import logging
from typing import Any, Dict, List, Optional
from src.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(BaseLLMProvider):
    """
    Provider for OpenAI and OpenAI-compatible Chat Completions APIs
    (OpenAI, OpenRouter, vLLM, LM Studio, Groq, Together, Azure OpenAI-compatible
    gateways, etc). Configurable via base_url, model, and api_key so any endpoint
    implementing the OpenAI Chat Completions wire format can be targeted.

    Attempts native structured outputs (response_format=json_schema, strict mode)
    first, falling back to json_object mode with best-effort JSON extraction for
    gateways/models that don't support strict schema enforcement.
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        timeout_seconds: float = 60.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/") if base_url else "https://api.openai.com/v1"
        self.model = model
        self.timeout = timeout_seconds
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client

        try:
            from openai import AsyncOpenAI
        except ImportError as err:
            logger.error("openai package not installed.")
            raise RuntimeError("openai is required for OpenAICompatibleProvider") from err

        self._client = AsyncOpenAI(
            api_key=self.api_key or "not-required",
            base_url=self.base_url,
            timeout=self.timeout,
        )
        return self._client

    @staticmethod
    def _build_user_content(prompt: str, images: Optional[List[str]] = None) -> Any:
        if not images:
            return prompt

        content: List[Dict[str, Any]] = [
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"},
            }
            for img_b64 in images
        ]
        content.append({"type": "text", "text": prompt})
        return content

    def _build_messages(
        self, prompt: str, system_prompt: str, images: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        messages: List[Dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": self._build_user_content(prompt, images)})
        return messages

    async def generate_structured(
        self,
        prompt: str,
        json_schema: Dict[str, Any],
        system_prompt: str = "",
        images: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        client = self._get_client()
        messages = self._build_messages(prompt, system_prompt, images)

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "extraction_schema",
                        "schema": json_schema,
                        "strict": True,
                    },
                },
            )
            raw_text = response.choices[0].message.content or ""
            return self._parse_json_payload(raw_text)
        except Exception as err:
            logger.warning(
                f"Strict json_schema mode failed on '{self.base_url}' ({err}); "
                "retrying with json_object mode."
            )

        schema_hint = (
            f"\n\nRespond ONLY with a JSON object strictly matching this JSON Schema:\n"
            f"{json.dumps(json_schema)}"
        )
        fallback_messages = self._build_messages(prompt + schema_hint, system_prompt, images)
        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=fallback_messages,
                temperature=0.0,
                response_format={"type": "json_object"},
            )
        except Exception as err:
            logger.error(f"OpenAI-compatible request error: {err}")
            raise RuntimeError(f"OpenAI-compatible inference failed: {err}") from err

        raw_text = response.choices[0].message.content or ""
        try:
            return self._parse_json_payload(raw_text)
        except Exception as err:
            logger.error(f"Failed to parse OpenAI-compatible output as JSON: {raw_text}")
            raise ValueError(f"OpenAI-compatible provider produced invalid JSON: {raw_text}") from err

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str = "",
        images: Optional[List[str]] = None,
    ) -> str:
        client = self._get_client()
        messages = self._build_messages(prompt, system_prompt, images)

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0,
            )
        except Exception as err:
            logger.error(f"OpenAI-compatible request error: {err}")
            raise RuntimeError(f"OpenAI-compatible text generation failed: {err}") from err

        return (response.choices[0].message.content or "").strip()

    @staticmethod
    def _parse_json_payload(text: str) -> Dict[str, Any]:
        """
        Parses JSON from model response, handling direct JSON, markdown code fences,
        and surrounding text preamble/postscript if present.
        """
        cleaned = text.strip() if text else ""
        if not cleaned:
            raise ValueError("Empty response received from OpenAI-compatible provider")

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

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
