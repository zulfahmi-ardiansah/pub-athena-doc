import base64
import json
import logging
import os
from typing import Any, Dict, List, Optional
from src.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class GoogleGenAIProvider(BaseLLMProvider):
    """
    Unified Google Cloud Gemini provider.
    Supports:
    - Google Cloud Vertex AI with Project ID & Location (gcloud ADC or Service Account)
    - API Key authentication (Google AI Studio / Gemini API)
    - Ambient gcloud authentication detection (auto-resolves project from `gcloud`/ADC if not set)
    """

    def __init__(
        self,
        api_key: str = "",
        project_id: str = "",
        location: str = "us-central1",
        credentials_file: str = "",
        model: str = "gemini-1.5-flash",
    ) -> None:
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        self.project_id = project_id or os.getenv("GOOGLE_PROJECT_ID", "")
        self.location = location or os.getenv("GOOGLE_LOCATION", "us-central1")
        self.credentials_file = credentials_file or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
        self.model = model
        self._client = None

        if self.credentials_file and os.path.exists(self.credentials_file):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.credentials_file

    @staticmethod
    def _sanitize_schema_for_gemini(schema: Any) -> Any:
        """
        Recursively strips OpenAPI 3.1 / JSON Schema draft fields (like 'examples')
        that Vertex AI / Google GenAI types.Schema strictly forbids.
        """
        if isinstance(schema, dict):
            cleaned = {}
            for k, v in schema.items():
                if k in ("examples", "$defs"):
                    continue
                if k == "properties" and isinstance(v, dict):
                    cleaned[k] = {
                        prop_k: GoogleGenAIProvider._sanitize_schema_for_gemini(prop_v)
                        for prop_k, prop_v in v.items()
                    }
                elif isinstance(v, (dict, list)):
                    cleaned[k] = GoogleGenAIProvider._sanitize_schema_for_gemini(v)
                else:
                    cleaned[k] = v
            return cleaned
        elif isinstance(schema, list):
            return [GoogleGenAIProvider._sanitize_schema_for_gemini(item) for item in schema]
        return schema

    def _get_client(self):
        if self._client is not None:
            return self._client

        try:
            from google import genai

            # Check if project_id is provided or can be auto-detected from gcloud ADC
            project_to_use = self.project_id
            if not project_to_use and not self.api_key:
                try:
                    import google.auth
                    _, default_project = google.auth.default()
                    if default_project:
                        project_to_use = default_project
                except Exception:
                    pass

            if project_to_use:
                # Vertex AI mode using gcloud ADC / Service Account
                logger.info(f"Initializing Google GenAI client in Vertex AI mode (project={project_to_use}, location={self.location})")
                
                # Attach quota project to ADC credentials if available to satisfy Vertex AI requirements
                creds = None
                try:
                    import google.auth
                    default_creds, _ = google.auth.default()
                    if hasattr(default_creds, "with_quota_project"):
                        creds = default_creds.with_quota_project(project_to_use)
                except Exception:
                    pass

                self._client = genai.Client(
                    vertexai=True,
                    project=project_to_use,
                    location=self.location,
                    credentials=creds,
                )
            elif self.api_key:
                # API Key mode
                self._client = genai.Client(api_key=self.api_key)
            else:
                # Default credentials fallback
                self._client = genai.Client()
        except ImportError as err:
            logger.error("google-genai package not installed.")
            raise RuntimeError("google-genai is required for GoogleGenAIProvider") from err
        except Exception as err:
            logger.error(f"Failed to initialize Google GenAI client: {err}")
            raise RuntimeError(f"Google GenAI client initialization failed: {err}") from err

        return self._client

    @staticmethod
    def _parse_json_payload(text: str) -> Dict[str, Any]:
        """
        Parses JSON from model response, handling direct JSON, markdown code fences,
        and surrounding text preamble/postscript if present.
        """
        cleaned = text.strip() if text else ""
        if not cleaned:
            raise ValueError("Empty response received from Google GenAI provider")

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

    async def generate_structured(
        self,
        prompt: str,
        json_schema: Dict[str, Any],
        system_prompt: str = "",
        images: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        client = self._get_client()
        from google.genai import types

        sanitized_schema = self._sanitize_schema_for_gemini(json_schema)
        # Strip publisher prefix if specified as google/model-name
        model_name = self.model.removeprefix("google/")

        config = types.GenerateContentConfig(
            system_instruction=system_prompt if system_prompt else None,
            response_mime_type="application/json",
            response_schema=sanitized_schema,
            temperature=0.0,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        parts: List[Any] = []
        if images:
            for img_b64 in images:
                img_bytes = base64.b64decode(img_b64)
                parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))

        parts.append(types.Part.from_text(text=prompt))
        contents = parts if len(parts) > 1 else prompt

        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config
        )

        if not response.text:
            raise RuntimeError("Google GenAI returned empty response")

        return self._parse_json_payload(response.text)

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str = "",
        images: Optional[List[str]] = None,
    ) -> str:
        client = self._get_client()
        from google.genai import types

        model_name = self.model.removeprefix("google/")
        config = types.GenerateContentConfig(
            system_instruction=system_prompt if system_prompt else None,
            temperature=0.0,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        parts: List[Any] = []
        if images:
            for img_b64 in images:
                img_bytes = base64.b64decode(img_b64)
                parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))

        parts.append(types.Part.from_text(text=prompt))
        contents = parts if len(parts) > 1 else prompt

        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config
        )

        return response.text.strip() if response.text else ""
