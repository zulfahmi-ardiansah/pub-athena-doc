import io
import pytest
from unittest.mock import AsyncMock, MagicMock
from PIL import Image
from src.config.settings import Settings
from src.engines.base import ExtractionError
from src.engines.factory import create_engine
from src.engines.string_engine import StringEngine
from src.engines.visual_engine import VisualEngine
from src.engines.hybrid_engine import HybridEngine
from src.modules.base import ExtractionOutput
from src.modules.extractors.base import BaseTextExtractor
from src.modules.analyzers.string_analyzer import StringTextAnalyzer
from src.modules.analyzers.llm_analyzer import LlmTextAnalyzer
from src.modules.analyzers.visual_llm_analyzer import VisualLlmAnalyzer
from src.domain.documents.identity_card import IdentityCardDocument
from src.domain.documents.tax_number import TaxNumberDocument
from src.providers.base import BaseLLMProvider


def _create_sample_png_bytes(width=100, height=50, color=(255, 255, 255)) -> bytes:
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Factory Tests
# ---------------------------------------------------------------------------

def test_factory_creates_string_engine():
    settings = Settings(
        engine_type="string_engine",
        ocr_backend="rapidocr",
    )
    engine = create_engine(settings)
    assert isinstance(engine, StringEngine)
    assert engine.name == "string_engine"


def test_factory_creates_visual_engine():
    settings = Settings(
        engine_type="visual_engine",
        llm_provider="ollama",
        ollama_vision_model="llama3.2-vision",
    )
    engine = create_engine(settings)
    assert isinstance(engine, VisualEngine)
    assert engine.name == "visual_engine"


def test_factory_creates_hybrid_engine():
    settings = Settings(
        engine_type="hybrid_engine",
        ocr_backend="rapidocr",
        extraction_pipeline="digital_pdf,ocr,visual_llm",
        analysis_mode="llm",
    )
    engine = create_engine(settings)
    assert isinstance(engine, HybridEngine)
    assert engine.name == "hybrid_engine"
    assert "digital_pdf" in engine.extractors
    assert "ocr" in engine.extractors
    assert "visual_llm" in engine.extractors
    assert "llm" in engine.analyzers
    assert "string" in engine.analyzers


def test_factory_creates_hybrid_engine_with_heterogeneous_providers():
    settings = Settings(
        engine_type="hybrid_engine",
        llm_text_provider="google",
        llm_vision_provider="ollama",
        google_api_key="fake-key",
        extraction_pipeline="digital_pdf,ocr,visual_llm",
        analysis_mode="llm",
    )
    engine = create_engine(settings)
    assert isinstance(engine, HybridEngine)
    assert settings.get_text_provider_type() == "google"
    assert settings.get_vision_provider_type() == "ollama"


# ---------------------------------------------------------------------------
# String Engine Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_string_engine_end_to_end():
    mock_ocr = MagicMock(spec=BaseTextExtractor)
    mock_ocr.extract_text = AsyncMock(return_value=ExtractionOutput(
        text=(
            "PROVINSI DKI JAKARTA\n"
            "JAKARTA PUSAT\n"
            "NIK : 3171010101900001\n"
            "Nama : BUDI SANTOSO\n"
            "Tempat/Tgl Lahir : JAKARTA, 01-01-1990\n"
            "Jenis Kelamin : LAKI-LAKI\n"
            "Alamat : JL TAMAN SUROPATI NO. 7\n"
            "RT/RW : 005/005\n"
            "Kel/Desa : MENTENG\n"
            "Kecamatan : MENTENG\n"
            "Agama : ISLAM\n"
            "Status Perkawinan : KAWIN\n"
            "Pekerjaan : KARYAWAN SWASTA\n"
            "Kewarganegaraan : WNI\n"
            "Berlaku Hingga : SEUMUR HIDUP"
        ),
        confidence=0.95,
        stage_name="ocr_rapidocr"
    ))

    engine = StringEngine(
        ocr_extractor=mock_ocr,
        analyzer=StringTextAnalyzer()
    )
    doc = IdentityCardDocument()

    result = await engine.extract(
        file_bytes=_create_sample_png_bytes(),
        filename="ktp.png",
        content_type="image/png",
        document=doc,
        trace=True
    )
    assert result.data["id_number"] == "3171010101900001"
    assert result.data["full_name"] == "BUDI SANTOSO"
    assert result.data["province"] == "DKI JAKARTA"
    assert result.trace is not None


# ---------------------------------------------------------------------------
# Visual Engine Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_visual_engine_end_to_end():
    mock_provider = MagicMock(spec=BaseLLMProvider)
    mock_provider.generate_structured = AsyncMock(return_value={
        "tax_number": "12.345.678.9-636.000",
        "tax_payer": "PT CONTOH MAKMUR",
        "branch_office": "KPP MADYA GRESIK",
        "branch_address": "JL DR WAHIDIN SUDIROHUSODO 700 GRESIK",
        "registration_date": "01-01-2022"
    })

    analyzer = VisualLlmAnalyzer(vision_provider=mock_provider)
    engine = VisualEngine(analyzer=analyzer)
    doc = TaxNumberDocument()

    result = await engine.extract(
        file_bytes=_create_sample_png_bytes(),
        filename="npwp.png",
        content_type="image/png",
        document=doc,
        trace=True
    )
    assert result.data["tax_number"] == "12.345.678.9-636.000"
    assert result.data["tax_payer"] == "PT CONTOH MAKMUR"
    assert result.trace is not None


# ---------------------------------------------------------------------------
# Hybrid Engine Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hybrid_engine_fallback_pdf_to_ocr():
    # 1. Digital PDF extractor returns low confidence
    mock_pdf = MagicMock(spec=BaseTextExtractor)
    mock_pdf.extract_text = AsyncMock(return_value=ExtractionOutput(
        text="Scanned raster page",
        confidence=0.1,
        stage_name="digital_pdf"
    ))

    # 2. OCR extractor succeeds with high confidence
    mock_ocr = MagicMock(spec=BaseTextExtractor)
    mock_ocr.extract_text = AsyncMock(return_value=ExtractionOutput(
        text="PROVINSI DKI JAKARTA\nNIK : 3171010101900001\nNama : BUDI SANTOSO",
        confidence=0.92,
        stage_name="ocr_rapidocr"
    ))

    # 3. LLM Analyzer
    mock_provider = MagicMock(spec=BaseLLMProvider)
    mock_provider.generate_structured = AsyncMock(return_value={
        "id_number": "3171010101900001",
        "full_name": "BUDI SANTOSO",
        "province": "DKI JAKARTA"
    })

    engine = HybridEngine(
        extractors={"digital_pdf": mock_pdf, "ocr": mock_ocr},
        analyzers={"llm": LlmTextAnalyzer(llm_provider=mock_provider), "string": StringTextAnalyzer()},
        pipeline=["digital_pdf", "ocr"],
        min_confidence=0.5,
        analysis_mode="llm"
    )

    doc = IdentityCardDocument()
    result = await engine.extract(
        file_bytes=b"%PDF-1.4 dummy",
        filename="doc.pdf",
        content_type="application/pdf",
        document=doc,
        trace=True
    )
    assert result.data["id_number"] == "3171010101900001"
    assert result.trace is not None
    stage_1 = result.trace["stages"][0]
    assert stage_1["name"] == "extraction_pipeline"
    assert stage_1["details"]["selected_stage"] == "ocr_rapidocr"


@pytest.mark.asyncio
async def test_hybrid_engine_fallback_ocr_to_visual_llm():
    # 1. OCR returns low confidence (<0.5)
    mock_ocr = MagicMock(spec=BaseTextExtractor)
    mock_ocr.extract_text = AsyncMock(return_value=ExtractionOutput(
        text="blurry illegible tokens",
        confidence=0.25,
        stage_name="ocr_rapidocr"
    ))

    # 2. Visual LLM extractor returns high confidence (0.90)
    mock_vision = MagicMock(spec=BaseTextExtractor)
    mock_vision.extract_text = AsyncMock(return_value=ExtractionOutput(
        text="PROVINSI DKI JAKARTA\nNIK : 3171010101900001\nNama : BUDI SANTOSO",
        confidence=0.90,
        stage_name="visual_llm"
    ))

    engine = HybridEngine(
        extractors={"ocr": mock_ocr, "visual_llm": mock_vision},
        analyzers={"string": StringTextAnalyzer()},
        pipeline=["ocr", "visual_llm"],
        min_confidence=0.5,
        analysis_mode="string"
    )

    doc = IdentityCardDocument()
    result = await engine.extract(
        file_bytes=_create_sample_png_bytes(),
        filename="blurry.png",
        content_type="image/png",
        document=doc,
        trace=True
    )
    assert result.data["id_number"] == "3171010101900001"
    assert result.trace is not None
    stage_1 = result.trace["stages"][0]
    assert stage_1["details"]["selected_stage"] == "visual_llm"


@pytest.mark.asyncio
async def test_hybrid_engine_empty_file_raises():
    engine = HybridEngine(extractors={}, analyzers={})
    doc = IdentityCardDocument()
    with pytest.raises(ExtractionError) as exc_info:
        await engine.extract(
            file_bytes=b"",
            filename="empty.png",
            content_type="image/png",
            document=doc,
            trace=True
        )
    assert "Empty file" in exc_info.value.message


@pytest.mark.asyncio
async def test_hybrid_engine_warmup():
    mock_vision_provider = MagicMock(spec=BaseLLMProvider)
    mock_vision_provider.preload = AsyncMock(return_value=True)

    mock_extractor = MagicMock()
    mock_extractor.vision_provider = mock_vision_provider

    engine = HybridEngine(
        extractors={"visual_llm": mock_extractor},
        analyzers={}
    )
    await engine.warmup()
    mock_vision_provider.preload.assert_awaited_once()
