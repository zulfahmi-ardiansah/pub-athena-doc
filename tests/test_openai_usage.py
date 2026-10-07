from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.config.settings import Settings
from src.engines.factory import create_llm_provider
from src.providers.openai_provider import OpenAICompatibleProvider
from src.utility.usage_cost import RequestUsage, track_usage


def _response(text: str, input_tokens: int, output_tokens: int, cached_tokens: int = 0):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            prompt_tokens_details=SimpleNamespace(cached_tokens=cached_tokens),
        ),
    )


def test_openai_compatible_uses_explicit_provider_name() -> None:
    assert OpenAICompatibleProvider().billing_service == "openai"
    assert OpenAICompatibleProvider(
        base_url="https://workspace.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
        provider_name="alibaba",
    ).billing_service == "alibaba"
    assert OpenAICompatibleProvider(
        base_url="https://openrouter.ai/api/v1", provider_name="openrouter"
    ).billing_service == "openrouter"


def test_openai_provider_setting_reaches_pricing_service() -> None:
    settings = Settings(
        llm_provider="openai",
        llm_text_provider="openai",
        openai_provider="alibaba",
        openai_text_model="qwen3.7-flash",
    )

    provider = create_llm_provider(settings)

    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.billing_service == "alibaba"
    assert provider.model == "qwen3.7-flash"


@pytest.mark.asyncio
async def test_openai_compatible_records_structured_fallback_and_text_calls() -> None:
    provider = OpenAICompatibleProvider(model="example-model")
    client = MagicMock()
    client.chat.completions.create = AsyncMock(side_effect=[
        _response("invalid JSON", 100, 20, 10),
        _response('{"value":"ok"}', 150, 30, 20),
        _response("transcribed", 50, 10),
    ])
    provider._client = client
    usage = RequestUsage()

    with track_usage(usage):
        result = await provider.generate_structured(
            prompt="extract", json_schema={"type": "object", "properties": {"value": {"type": "string"}}}
        )
        text = await provider.generate_text(prompt="transcribe")

    assert result == {"value": "ok"}
    assert text == "transcribed"
    assert len(usage.events) == 3
    assert [event.input_tokens for event in usage.events] == [100, 150, 50]
    assert [event.output_tokens for event in usage.events] == [20, 30, 10]
    assert [event.cached_input_tokens for event in usage.events] == [10, 20, 0]


@pytest.mark.asyncio
async def test_openai_compatible_marks_missing_usage_unknown() -> None:
    provider = OpenAICompatibleProvider(model="example-model")
    client = MagicMock()
    response = _response("text", 1, 1)
    response.usage = None
    client.chat.completions.create = AsyncMock(return_value=response)
    provider._client = client
    usage = RequestUsage()

    with track_usage(usage):
        assert await provider.generate_text(prompt="transcribe") == "text"

    assert usage.events[0].input_tokens is None
    assert usage.summarize(None)["estimate_cost"] is None
