import io
import pytest
from unittest.mock import AsyncMock, MagicMock
from PIL import Image
from src.config.settings import Settings
from src.engines.factory import create_engine
from src.engines.ocr_hybrid_engine import OcrHybridEngine, LocalCpuEngine
from src.engines.visual_model_engine import VisualModelEngine
from src.providers.ollama_provider import OllamaProvider
from src.domain.documents.identity_card import IdentityCardDocument


def test_factory_creates_ocr_hybrid_with_rapidocr():
    settings = Settings(
        engine_backend="ocr_hybrid",
        ocr_engine="rapidocr",
    )
    engine = create_engine(settings)
    assert isinstance(engine, OcrHybridEngine)
    assert engine.ocr_engine_type == "rapidocr"


def test_factory_creates_ocr_hybrid_with_tesseract():
    settings = Settings(
        engine_backend="ocr_hybrid",
        ocr_engine="tesseract",
        tesseract_cmd="/usr/bin/tesseract"
    )
    engine = create_engine(settings)
    assert isinstance(engine, OcrHybridEngine)
    assert engine.ocr_engine_type == "tesseract"
    assert engine.tesseract_cmd == "/usr/bin/tesseract"


def test_factory_creates_local_cpu_alias():
    settings = Settings(
        engine_backend="local_cpu",
        ocr_engine="rapidocr",
    )
    engine = create_engine(settings)
    assert isinstance(engine, OcrHybridEngine)
    assert isinstance(engine, LocalCpuEngine)


def test_factory_creates_visual_model():
    settings = Settings(
        engine_backend="visual_model",
        ollama_vision_model="llama3.2-vision",
    )
    engine = create_engine(settings)
    assert isinstance(engine, VisualModelEngine)


def test_ocr_hybrid_engine_tesseract_handles_dict(monkeypatch):
    img = Image.new("RGB", (10, 10), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    dummy_bytes = buf.getvalue()

    engine = OcrHybridEngine(
        llm_provider=MagicMock(),
        ocr_engine_type="tesseract",
    )

    mock_pytesseract = MagicMock()
    mock_pytesseract.image_to_string.return_value = {"text": "  Extracted Text from Dict  "}
    monkeypatch.setattr("pytesseract.image_to_string", mock_pytesseract.image_to_string)

    result = engine._run_ocr_on_bytes(dummy_bytes)
    assert result == "Extracted Text from Dict"


def test_ocr_hybrid_engine_tesseract_handles_str(monkeypatch):
    img = Image.new("RGB", (10, 10), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    dummy_bytes = buf.getvalue()

    engine = OcrHybridEngine(
        llm_provider=MagicMock(),
        ocr_engine_type="tesseract",
    )

    mock_pytesseract = MagicMock()
    mock_pytesseract.image_to_string.return_value = "  Extracted Text from Str  "
    monkeypatch.setattr("pytesseract.image_to_string", mock_pytesseract.image_to_string)

    result = engine._run_ocr_on_bytes(dummy_bytes)
    assert result == "Extracted Text from Str"


@pytest.mark.asyncio
async def test_ollama_provider_preload(monkeypatch):
    provider = OllamaProvider(
        base_url="http://localhost:11434",
        model="qwen2.5:3b",
        keep_alive="-1"
    )

    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_client.post.return_value = mock_response

    class MockAsyncClientContext:
        async def __aenter__(self):
            return mock_client
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: MockAsyncClientContext())

    success = await provider.preload()
    assert success is True
    mock_client.post.assert_called_once_with(
        "http://localhost:11434/api/generate",
        json={"model": "qwen2.5:3b", "keep_alive": -1}
    )


@pytest.mark.asyncio
async def test_ollama_provider_generate_structured_with_images(monkeypatch):
    provider = OllamaProvider(
        base_url="http://localhost:11434",
        model="llama3.2-vision",
    )

    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"response": '{"id_number": "3171012345678901", "full_name": "BUDI"}'}
    mock_client.post.return_value = mock_response

    class MockAsyncClientContext:
        async def __aenter__(self):
            return mock_client
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: MockAsyncClientContext())

    res = await provider.generate_structured(
        prompt="Extract KTP",
        json_schema={"type": "object"},
        system_prompt="Rules",
        images=["base64_encoded_dummy"]
    )

    assert res == {"id_number": "3171012345678901", "full_name": "BUDI"}
    call_args = mock_client.post.call_args[1]["json"]
    assert "images" in call_args
    assert call_args["images"] == ["base64_encoded_dummy"]


@pytest.mark.asyncio
async def test_ocr_hybrid_engine_warmup():
    mock_provider = AsyncMock()
    mock_provider.preload = AsyncMock(return_value=True)

    engine = OcrHybridEngine(
        llm_provider=mock_provider,
        ocr_engine_type="rapidocr",
    )

    await engine.warmup()
    mock_provider.preload.assert_awaited_once()


@pytest.mark.asyncio
async def test_visual_model_engine_extract_image():
    # Create dummy PNG image bytes
    img = Image.new("RGB", (20, 20), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    dummy_img_bytes = buf.getvalue()

    mock_provider = AsyncMock()
    mock_provider.generate_structured = AsyncMock(return_value={
        "id_number": "3171012345678901",
        "full_name": "AHMAD TEST",
        "birth_place": "JAKARTA",
        "birth_date": "1990-01-01",
        "gender": "LAKI-LAKI",
        "blood_type": "O",
        "address": "JL SUDIRMAN NO 1",
        "neighborhood_unit": "001",
        "community_unit": "002",
        "village": "GELORA",
        "district": "TANAH ABANG",
        "religion": "ISLAM",
        "marital_status": "KAWIN",
        "occupation": "KARYAWAN SWASTA",
        "nationality": "WNI",
        "expiry_date": "SEUMUR HIDUP"
    })

    engine = VisualModelEngine(llm_provider=mock_provider)
    doc = IdentityCardDocument()

    result = await engine.extract(
        file_bytes=dummy_img_bytes,
        filename="ktp_sample.png",
        content_type="image/png",
        document=doc
    )

    assert result["id_number"] == "3171012345678901"
    assert result["full_name"] == "AHMAD TEST"
    mock_provider.generate_structured.assert_awaited_once()
    kwargs = mock_provider.generate_structured.call_args[1]
    assert "images" in kwargs
    assert len(kwargs["images"]) == 1


@pytest.mark.asyncio
async def test_visual_model_engine_warmup():
    mock_provider = AsyncMock()
    mock_provider.preload = AsyncMock(return_value=True)

    engine = VisualModelEngine(llm_provider=mock_provider)
    await engine.warmup()
    mock_provider.preload.assert_awaited_once()


@pytest.mark.asyncio
async def test_visual_model_engine_extract_pdf():
    import fitz

    # Create dummy 1-page PDF
    pdf_doc = fitz.open()
    page = pdf_doc.new_page(width=100, height=100)
    page.draw_rect(fitz.Rect(10, 10, 90, 90), color=(0, 0, 1), fill=(1, 1, 1))
    dummy_pdf_bytes = pdf_doc.tobytes()
    pdf_doc.close()

    mock_provider = AsyncMock()
    mock_provider.generate_structured = AsyncMock(return_value={
        "id_number": "3171012345678901",
        "full_name": "PDF TEST",
        "birth_place": "JAKARTA",
        "birth_date": "1990-01-01",
        "gender": "LAKI-LAKI",
        "blood_type": "O",
        "address": "JL SUDIRMAN NO 1",
        "neighborhood_unit": "001",
        "community_unit": "002",
        "village": "GELORA",
        "district": "TANAH ABANG",
        "religion": "ISLAM",
        "marital_status": "KAWIN",
        "occupation": "KARYAWAN SWASTA",
        "nationality": "WNI",
        "expiry_date": "SEUMUR HIDUP"
    })

    engine = VisualModelEngine(llm_provider=mock_provider)
    doc = IdentityCardDocument()

    result = await engine.extract(
        file_bytes=dummy_pdf_bytes,
        filename="sample.pdf",
        content_type="application/pdf",
        document=doc
    )

    assert result["id_number"] == "3171012345678901"
    assert result["full_name"] == "PDF TEST"
    mock_provider.generate_structured.assert_awaited_once()
    kwargs = mock_provider.generate_structured.call_args[1]
    assert "images" in kwargs
    assert len(kwargs["images"]) == 1

