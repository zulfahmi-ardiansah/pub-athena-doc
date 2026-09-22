import io
import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from PIL import Image
from src.modules.base import ExtractionOutput, PreprocessResult
from src.modules.preprocessors.image_preprocessor import ImagePreprocessor
from src.modules.extractors.digital_pdf import DigitalPdfExtractor
from src.modules.extractors.ocr_extractor import OcrExtractor
from src.modules.extractors.visual_llm_extractor import VisualLlmExtractor
from src.modules.analyzers.string_analyzer import StringTextAnalyzer
from src.modules.analyzers.llm_analyzer import LlmTextAnalyzer
from src.modules.analyzers.visual_llm_analyzer import VisualLlmAnalyzer
from src.domain.documents.identity_card import IdentityCardDocument, IdentityCardSchema
from src.domain.documents.tax_number import TaxNumberDocument, TaxNumberSchema
from src.providers.google_provider import GoogleGenAIProvider


def _create_sample_png_bytes(width=100, height=50, color=(255, 255, 255)) -> bytes:
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Preprocessor Tests
# ---------------------------------------------------------------------------

def test_image_preprocessor_disabled():
    img_bytes = _create_sample_png_bytes()
    prep = ImagePreprocessor(enabled=False)
    res = prep.preprocess(img_bytes)
    assert isinstance(res, PreprocessResult)
    assert res.processed_bytes == img_bytes
    assert res.metadata.get("preprocessing_enabled") is False


def test_image_preprocessor_enabled():
    img_bytes = _create_sample_png_bytes()
    prep = ImagePreprocessor(enabled=True, deskew=True, enhance_contrast=True)
    res = prep.preprocess(img_bytes)
    assert isinstance(res, PreprocessResult)
    assert len(res.processed_bytes) > 0


def test_image_preprocessor_normalize():
    img_bytes = _create_sample_png_bytes(width=80, height=40)
    prep = ImagePreprocessor()
    norm_bytes, dims = prep.normalize_image(img_bytes)
    assert dims == (80, 40)
    assert len(norm_bytes) > 0


# ---------------------------------------------------------------------------
# Extractor Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_digital_pdf_extractor_empty():
    extractor = DigitalPdfExtractor()
    out = await extractor.extract_text(b"not a real pdf", filename="test.pdf", content_type="application/pdf")
    assert isinstance(out, ExtractionOutput)
    assert out.confidence == 0.0
    assert out.is_empty


@pytest.mark.asyncio
async def test_ocr_extractor_rapidocr_mock(monkeypatch):
    extractor = OcrExtractor(backend="rapidocr")
    mock_rapid = MagicMock()
    mock_rapid.return_value = (
        [[[0, 0], "PROVINSI DKI JAKARTA", 0.95], [[0, 0], "NIK 3171010101900001", 0.90]],
        0.05
    )
    extractor._rapid_ocr = mock_rapid

    img_bytes = _create_sample_png_bytes()
    out = await extractor.extract_text(img_bytes, filename="ktp.png", content_type="image/png")
    assert "PROVINSI DKI JAKARTA" in out.text
    assert out.confidence >= 0.90
    assert out.stage_name == "ocr_rapidocr"


@pytest.mark.asyncio
async def test_ocr_extractor_tesseract_mock(monkeypatch):
    extractor = OcrExtractor(backend="tesseract")
    mock_pytesseract = MagicMock()
    mock_pytesseract.image_to_data.return_value = {
        "text": ["KPP", "MADYA", "GRESIK"],
        "conf": ["95", "90", "88"],
    }
    monkeypatch.setattr("pytesseract.image_to_data", mock_pytesseract.image_to_data)

    img_bytes = _create_sample_png_bytes()
    out = await extractor.extract_text(img_bytes, filename="npwp.png", content_type="image/png")
    assert "KPP MADYA GRESIK" in out.text
    assert out.confidence >= 0.85
    assert out.stage_name == "ocr_tesseract"


@pytest.mark.asyncio
async def test_ocr_extractor_google_vision_project_id_mock(monkeypatch):
    import sys
    mock_vision_mod = MagicMock()
    mock_vision_mod.Image.side_effect = lambda content: MagicMock(content=content)
    monkeypatch.setitem(sys.modules, "google.cloud", MagicMock(vision=mock_vision_mod))
    monkeypatch.setitem(sys.modules, "google.cloud.vision", mock_vision_mod)

    extractor = OcrExtractor(backend="google_vision", google_project_id="my-gcp-project")
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.error.message = None
    mock_response.full_text_annotation.text = "PROVINSI DKI JAKARTA\nNIK 3171010101900001"
    mock_page = MagicMock()
    mock_page.confidence = 0.96
    mock_response.full_text_annotation.pages = [mock_page]
    mock_client.document_text_detection.return_value = mock_response
    extractor._vision_client = mock_client

    img_bytes = _create_sample_png_bytes()
    out = await extractor.extract_text(img_bytes, filename="ktp.png", content_type="image/png")
    assert "3171010101900001" in out.text
    assert out.confidence == 0.96
    assert out.stage_name == "ocr_google_vision"


@pytest.mark.asyncio
async def test_visual_llm_extractor():
    mock_provider = AsyncMock()
    mock_provider.generate_text = AsyncMock(return_value="PROVINSI DKI JAKARTA\nNIK 3171010101900001")
    extractor = VisualLlmExtractor(vision_provider=mock_provider)

    img_bytes = _create_sample_png_bytes()
    out = await extractor.extract_text(img_bytes, filename="ktp.png", content_type="image/png")
    assert "3171010101900001" in out.text
    assert out.confidence == 0.90
    assert out.stage_name == "visual_llm"


# ---------------------------------------------------------------------------
# Analyzer Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_string_text_analyzer():
    analyzer = StringTextAnalyzer()
    doc = IdentityCardDocument()
    raw_text = "PROVINSI DKI JAKARTA\nJAKARTA PUSAT\nNIK : 3171010101900001\nNama : BUDI"
    result = await analyzer.analyze(input_data=raw_text, document=doc)
    assert isinstance(result, dict)
    assert result["id_number"] == "3171010101900001"
    assert result["province"] == "DKI JAKARTA"
    assert result["name"] == "BUDI"


@pytest.mark.asyncio
async def test_llm_text_analyzer():
    mock_provider = AsyncMock()
    mock_provider.generate_structured = AsyncMock(return_value={
        "id_number": "3171010101900001",
        "name": "BUDI SANTOSO",
        "province": "DKI JAKARTA"
    })
    analyzer = LlmTextAnalyzer(llm_provider=mock_provider)
    doc = IdentityCardDocument()
    result = await analyzer.analyze(input_data="some raw ocr text", document=doc)
    assert result["id_number"] == "3171010101900001"
    assert result["name"] == "BUDI SANTOSO"


@pytest.mark.asyncio
async def test_visual_llm_analyzer():
    mock_provider = AsyncMock()
    mock_provider.generate_structured = AsyncMock(return_value={
        "tax_number": "12.345.678.9-636.000",
        "name": "PT CONTOH MAKMUR",
        "tax_office": "KPP MADYA GRESIK"
    })
    analyzer = VisualLlmAnalyzer(vision_provider=mock_provider)
    doc = TaxNumberDocument()
    img_bytes = _create_sample_png_bytes()
    result = await analyzer.analyze(input_data=[img_bytes], document=doc)
    assert result["tax_number"] == "12.345.678.9-636.000"
    assert result["name"] == "PT CONTOH MAKMUR"


def test_google_genai_provider_schema_sanitization():
    from google.genai import types
    identity_card_schema = IdentityCardSchema.model_json_schema()
    assert "examples" in identity_card_schema["properties"]["province"]
    sanitized_identity_card = GoogleGenAIProvider._sanitize_schema_for_gemini(identity_card_schema)
    assert "examples" not in sanitized_identity_card["properties"]["province"]
    validated_identity_card = types.Schema.model_validate(sanitized_identity_card)
    assert validated_identity_card is not None

    tax_number_schema = TaxNumberSchema.model_json_schema()
    sanitized_tax_number = GoogleGenAIProvider._sanitize_schema_for_gemini(tax_number_schema)
    validated_tax_number = types.Schema.model_validate(sanitized_tax_number)
    assert validated_tax_number is not None


def test_google_genai_provider_credential_modes(tmp_path):
    # 1. API Key mode
    provider_api_key = GoogleGenAIProvider(api_key="AIzaSyTestApiKey")
    assert provider_api_key.api_key == "AIzaSyTestApiKey"
    client_api = provider_api_key._get_client()
    assert client_api is not None

    # 2. JSON File path mode
    sample_key_file = tmp_path / "service_account.json"
    sample_key_file.write_text('{"type": "service_account", "project_id": "test-project-123"}', encoding="utf-8")
    provider_file = GoogleGenAIProvider(credentials_file=str(sample_key_file))
    assert provider_file.credentials_file == str(sample_key_file)
    assert os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") == str(sample_key_file)

