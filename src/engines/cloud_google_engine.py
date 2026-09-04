import json
import logging
from typing import Any, Dict, List, Optional
from src.domain.base import BaseDocument
from src.engines.base import BaseExtractionEngine, ExtractionResult
from src.providers.google_provider import GoogleGenAIProvider

logger = logging.getLogger(__name__)


class CloudGoogleEngine(BaseExtractionEngine):
    """
    Cloud Google engine leveraging Gemini 1.5 multimodal structured document extraction.
    """

    name = "cloud_google"

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash") -> None:
        self.api_key = api_key
        self.model = model
        self.provider = GoogleGenAIProvider(api_key=api_key, model=model)

    async def extract(
        self,
        file_bytes: bytes,
        filename: Optional[str],
        content_type: Optional[str],
        document: BaseDocument,
        trace: bool = False
    ) -> ExtractionResult:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured for CloudGoogleEngine")

        try:
            from google import genai
            from google.genai import types
        except ImportError as err:
            raise RuntimeError("google-genai package is required for CloudGoogleEngine") from err

        stages: List[Dict[str, Any]] = []

        mime = content_type or "application/pdf"
        if not content_type and filename:
            if filename.lower().endswith(".pdf"):
                mime = "application/pdf"
            elif filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                mime = "image/png"

        if trace:
            stages.append({
                "stage": 1,
                "name": "file_inspection",
                "details": {
                    "filename": filename,
                    "mime_type": mime,
                    "file_size_bytes": len(file_bytes)
                }
            })

        client = genai.Client(api_key=self.api_key)
        part = types.Part.from_bytes(data=file_bytes, mime_type=mime)
        system_prompt = document.build_system_prompt()
        json_schema = document.get_json_schema()

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=json_schema,
            temperature=0.0
        )

        prompt = f"Extract the information for {document.name} into the structured JSON schema."
        contents = types.Content(
            parts=[
                part,
                types.Part.from_text(text=prompt)
            ]
        )

        if trace:
            stages.append({
                "stage": 2,
                "name": "multimodal_prompt_construction",
                "details": {
                    "model": self.model,
                    "prompt": prompt,
                    "system_prompt": system_prompt,
                    "json_schema": json_schema
                }
            })

        response = client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config
        )

        if not response.text:
            raise RuntimeError("Gemini returned empty response text")

        parsed_json = json.loads(response.text)

        if trace:
            stages.append({
                "stage": 3,
                "name": "raw_gemini_response",
                "details": {
                    "raw_response_text": response.text,
                    "parsed_json": parsed_json
                }
            })

        validated_model = document.validate_payload(parsed_json)
        final_data = validated_model.model_dump()

        if trace:
            stages.append({
                "stage": 4,
                "name": "schema_validation",
                "details": {
                    "schema_class": document.schema_class.__name__,
                    "validated_fields": list(final_data.keys()),
                    "final_output": final_data
                }
            })

        trace_data = {"engine": self.name, "stages": stages} if trace else None
        return ExtractionResult(data=final_data, trace=trace_data)
