import pytest
from unittest.mock import AsyncMock, MagicMock
from src.domain.documents.identity_card import IdentityCardDocument
from src.engines.ocr_hybrid_engine import OcrHybridEngine
from src.providers.base import BaseLLMProvider


@pytest.mark.asyncio
async def test_local_cpu_engine_trace_output():
    mock_provider = MagicMock(spec=BaseLLMProvider)
    mock_provider.name = "ollama"
    mock_provider.model = "qwen2.5:3b"
    mock_provider.generate_structured = AsyncMock(return_value={
        "id_number": "3171010101900001",
        "full_name": "BUDI SANTOSO",
        "gender": "LAKI-LAKI",
        "valid_until": "SEUMUR HIDUP"
    })

    engine = OcrHybridEngine(llm_provider=mock_provider)
    doc = IdentityCardDocument()

    sample_text_bytes = b"NIK : 3171010101900001\nNama : BUDI SANTOSO"

    # 1. Test trace=False
    res_no_trace = await engine.extract(
        file_bytes=sample_text_bytes,
        filename="sample.txt",
        content_type="text/plain",
        document=doc,
        trace=False
    )
    assert res_no_trace.data["id_number"] == "3171010101900001"
    assert res_no_trace.trace is None

    # 2. Test trace=True
    res_with_trace = await engine.extract(
        file_bytes=sample_text_bytes,
        filename="sample.txt",
        content_type="text/plain",
        document=doc,
        trace=True
    )
    assert res_with_trace.data["id_number"] == "3171010101900001"
    assert res_with_trace.trace is not None
    assert res_with_trace.trace["engine"] == "ocr_hybrid"

    stage_names = [s["name"] for s in res_with_trace.trace["stages"]]
    assert "file_triage" in stage_names
    assert "raw_text_extraction" in stage_names
    assert "prompt_construction" in stage_names
    assert "llm_structured_output" in stage_names
    assert "schema_validation" in stage_names
