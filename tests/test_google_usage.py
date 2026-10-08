from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from google.auth.exceptions import RefreshError

from src.modules.extractors.ocr_extractor import OcrExtractor
from src.providers.google_provider import GoogleGenAIProvider
from src.utility.usage_cost import RequestUsage, track_usage


@pytest.mark.asyncio
async def test_gemini_service_account_uses_vertex_scope_for_structured_output(monkeypatch, tmp_path) -> None:
    from google import genai
    from google.oauth2 import service_account

    credentials_file = tmp_path / "service-account.json"
    credentials_file.write_text("{}", encoding="utf-8")
    credentials = MagicMock()
    credentials.with_quota_project.return_value = credentials
    client = MagicMock()
    client.models.generate_content.return_value = SimpleNamespace(text='{"value":"ok"}', usage_metadata=None)

    def load_credentials(path: str, *, scopes=None):
        assert path == str(credentials_file)
        if scopes != ["https://www.googleapis.com/auth/cloud-platform"]:
            raise RefreshError("invalid_scope: Invalid OAuth scope or ID token audience provided.")
        return credentials

    monkeypatch.setattr(service_account.Credentials, "from_service_account_file", load_credentials)
    monkeypatch.setattr(genai, "Client", lambda **kwargs: client if kwargs["credentials"] is credentials else None)
    provider = GoogleGenAIProvider(credentials_file=str(credentials_file), project_id="test-project")

    result = await provider.generate_structured("extract", {"type": "object"})

    assert result == {"value": "ok"}
    client.models.generate_content.assert_called_once()


@pytest.mark.asyncio
async def test_gemini_records_structured_and_text_usage() -> None:
    provider = GoogleGenAIProvider(api_key="test-key", model="google/example-model")
    provider._billing_service = "google_ai"
    response = SimpleNamespace(
        text='{"value":"ok"}',
        usage_metadata=SimpleNamespace(
            prompt_token_count=100,
            candidates_token_count=20,
            thoughts_token_count=5,
            cached_content_token_count=10,
            tool_use_prompt_token_count=0,
        ),
    )
    provider._client = MagicMock()
    provider._client.models.generate_content.return_value = response
    usage = RequestUsage()

    with track_usage(usage):
        result = await provider.generate_structured(
            prompt="extract", json_schema={"type": "object", "properties": {"value": {"type": "string"}}}
        )
        text = await provider.generate_text(prompt="transcribe")

    assert result == {"value": "ok"}
    assert text == '{"value":"ok"}'
    assert len(usage.events) == 2
    assert all(event.billing_service == "google_ai" for event in usage.events)
    assert all(event.model == "example-model" for event in usage.events)
    assert all(event.input_tokens == 100 for event in usage.events)
    assert all(event.output_tokens == 25 for event in usage.events)
    assert all(event.cached_input_tokens == 10 for event in usage.events)


@pytest.mark.parametrize("vertexai, service", [
    (False, "google_ai"),
    (True, "google_vertex"),
])
def test_gemini_ambient_credentials_use_selected_service(monkeypatch, vertexai, service) -> None:
    import google.auth
    from google import genai

    monkeypatch.setattr(google.auth, "default", lambda: (None, None))
    client = MagicMock(vertexai=vertexai)
    monkeypatch.setattr(genai, "Client", lambda: client)
    provider = GoogleGenAIProvider(credentials_file="missing-credentials.json")

    assert provider._get_client() is client
    assert provider._billing_service == service


@pytest.mark.asyncio
async def test_google_vision_records_one_unit_per_pdf_page(monkeypatch) -> None:
    import sys

    mock_vision = MagicMock()
    mock_vision.Image.side_effect = lambda content: MagicMock(content=content)
    monkeypatch.setitem(sys.modules, "google.cloud", MagicMock(vision=mock_vision))
    monkeypatch.setitem(sys.modules, "google.cloud.vision", mock_vision)

    preprocessor = MagicMock()
    preprocessor.render_pdf_to_images.return_value = [b"page-one", b"page-two"]
    preprocessor.preprocess.side_effect = lambda data: SimpleNamespace(processed_bytes=data, metadata={})
    extractor = OcrExtractor(backend="google_vision", preprocessor=preprocessor)
    response = MagicMock()
    response.error.message = None
    response.full_text_annotation.text = "visible text"
    response.full_text_annotation.pages = []
    extractor._vision_client = MagicMock()
    extractor._vision_client.document_text_detection.return_value = response
    usage = RequestUsage()

    with track_usage(usage):
        result = await extractor.extract_text(b"%PDF", filename="sample.pdf", content_type="application/pdf")

    assert result.metadata["page_count"] == 2
    assert len(usage.events) == 2
    assert all(event.billing_service == "google_vision" for event in usage.events)
    assert all(event.units == 1 for event in usage.events)
