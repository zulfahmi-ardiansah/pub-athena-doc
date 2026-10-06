import pytest
from unittest.mock import AsyncMock, MagicMock
from src.domain.documents.identity_card import IdentityCardDocument
from src.engines.hybrid_engine import HybridEngine
from src.engines.string_engine import StringEngine
from src.modules.extractors.ocr_extractor import OcrExtractor
from src.modules.analyzers.llm_analyzer import LlmTextAnalyzer
from src.modules.analyzers.string_analyzer import StringTextAnalyzer
from src.providers.base import BaseLLMProvider


@pytest.mark.asyncio
async def test_hybrid_engine_trace_output():
    mock_provider = MagicMock(spec=BaseLLMProvider)
    mock_provider.name = "ollama"
    mock_provider.model = "qwen2.5:3b"
    mock_provider.generate_structured = AsyncMock(return_value={
        "document_number": "3171010101900001",
        "holder_name": "BUDI SANTOSO",
        "gender": "LAKI-LAKI",
        "valid_until": "SEUMUR HIDUP"
    })

    mock_ocr = MagicMock(spec=OcrExtractor)
    from src.modules.base import ExtractionOutput
    mock_ocr.extract_text = AsyncMock(return_value=ExtractionOutput(
        text="NIK : 3171010101900001\nNama : BUDI SANTOSO",
        confidence=0.95,
        stage_name="ocr_rapidocr",
        metadata={"backend": "rapidocr"}
    ))

    engine = HybridEngine(
        extractors={"ocr": mock_ocr},
        analyzers={"text_llm": LlmTextAnalyzer(llm_provider=mock_provider)},
        pipeline=["ocr"],
        analysis_mode="text_llm"
    )
    doc = IdentityCardDocument()
    sample_text_bytes = b"sample_bytes"

    # 1. Test trace=False
    res_no_trace = await engine.extract(
        file_bytes=sample_text_bytes,
        filename="sample.png",
        content_type="image/png",
        document=doc,
        trace=False
    )
    assert res_no_trace.data["document_number"] == "3171010101900001"
    assert res_no_trace.trace is None

    # 2. Test trace=True
    res_with_trace = await engine.extract(
        file_bytes=sample_text_bytes,
        filename="sample.png",
        content_type="image/png",
        document=doc,
        trace=True
    )
    assert res_with_trace.data["document_number"] == "3171010101900001"
    assert res_with_trace.trace is not None
    assert res_with_trace.trace["engine"] == "hybrid_engine"

    stage_names = [s["name"] for s in res_with_trace.trace["stages"]]
    assert "extraction_pipeline" in stage_names
    assert "text_analysis" in stage_names


@pytest.mark.asyncio
async def test_string_engine_trace_output():
    mock_ocr = MagicMock(spec=OcrExtractor)
    from src.modules.base import ExtractionOutput
    mock_ocr.extract_text = AsyncMock(return_value=ExtractionOutput(
        text="PROVINSI DKI JAKARTA\nJAKARTA PUSAT\nNIK : 3171010101900001\nNama : BUDI SANTOSO",
        confidence=0.95,
        stage_name="ocr_rapidocr"
    ))

    engine = StringEngine(
        ocr_extractor=mock_ocr,
        analyzer=StringTextAnalyzer()
    )
    doc = IdentityCardDocument()

    res = await engine.extract(
        file_bytes=b"sample_bytes",
        filename="sample.png",
        content_type="image/png",
        document=doc,
        trace=True
    )
    assert res.data["document_number"] == "3171010101900001"
    assert res.trace is not None
    assert res.trace["engine"] == "string_engine"
    stage_names = [s["name"] for s in res.trace["stages"]]
    assert "text_extraction" in stage_names
    assert "string_analysis" in stage_names
