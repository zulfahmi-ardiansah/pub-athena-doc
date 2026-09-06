import json
import logging
from typing import Any, Dict, List, Optional
from src.domain.base import BaseDocument
from src.engines.base import BaseExtractionEngine, ExtractionResult, ExtractionError
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
        stages: List[Dict[str, Any]] = []

        if not self.api_key:
            err_msg = "GEMINI_API_KEY is not configured for CloudGoogleEngine"
            if trace:
                stages.append({
                    "stage": 1,
                    "name": "configuration_check",
                    "status": "failed",
                    "details": {"error": err_msg}
                })
            raise ExtractionError(
                message=err_msg,
                trace={"engine": self.name, "stages": stages} if trace else None
            )

        try:
            from google import genai
            from google.genai import types
        except ImportError as err:
            err_msg = "google-genai package is required for CloudGoogleEngine"
            if trace:
                stages.append({
                    "stage": 1,
                    "name": "dependency_check",
                    "status": "failed",
                    "details": {"error": err_msg}
                })
            raise ExtractionError(
                message=err_msg,
                trace={"engine": self.name, "stages": stages} if trace else None
            ) from err

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
                "status": "completed",
                "details": {
                    "filename": filename,
                    "mime_type": mime,
                    "file_size_bytes": len(file_bytes)
                }
            })

        system_prompt = document.build_system_prompt()
        json_schema = document.get_json_schema()
        prompt = f"Extract the information for {document.name} into the structured JSON schema."

        if trace:
            stages.append({
                "stage": 2,
                "name": "multimodal_prompt_construction",
                "status": "completed",
                "details": {
                    "model": self.model,
                    "prompt": prompt,
                    "system_prompt": system_prompt,
                    "json_schema": json_schema
                }
            })

        try:
            client = genai.Client(api_key=self.api_key)
            part = types.Part.from_bytes(data=file_bytes, mime_type=mime)

            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=json_schema,
                temperature=0.0
            )

            contents = types.Content(
                parts=[
                    part,
                    types.Part.from_text(text=prompt)
                ]
            )

            response = client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config
            )

            if not response.text:
                raise RuntimeError("Gemini returned empty response text")

            parsed_json = json.loads(response.text)
        except Exception as exc:
            if trace:
                stages.append({
                    "stage": 3,
                    "name": "raw_gemini_response",
                    "status": "failed",
                    "details": {
                        "error": str(exc),
                        "error_type": exc.__class__.__name__
                    }
                })
            raise ExtractionError(
                message=str(exc),
                trace={"engine": self.name, "stages": stages} if trace else None
            ) from exc

        if trace:
            stages.append({
                "stage": 3,
                "name": "raw_gemini_response",
                "status": "completed",
                "details": {
                    "raw_response_text": response.text,
                    "parsed_json": parsed_json
                }
            })

        try:
            validated_model = document.validate_payload(parsed_json)
            final_data = validated_model.model_dump()
        except Exception as exc:
            if trace:
                stages.append({
                    "stage": 4,
                    "name": "schema_validation",
                    "status": "failed",
                    "details": {
                        "schema_class": document.schema_class.__name__,
                        "error": str(exc),
                        "error_type": exc.__class__.__name__,
                        "raw_input": parsed_json
                    }
                })
            raise ExtractionError(
                message=str(exc),
                trace={"engine": self.name, "stages": stages} if trace else None,
                raw_data=parsed_json if isinstance(parsed_json, dict) else None
            ) from exc

        if trace:
            stages.append({
                "stage": 4,
                "name": "schema_validation",
                "status": "completed",
                "details": {
                    "schema_class": document.schema_class.__name__,
                    "validated_fields": list(final_data.keys()),
                    "final_output": final_data
                }
            })

        trace_data = {"engine": self.name, "stages": stages} if trace else None
        return ExtractionResult(data=final_data, trace=trace_data)
