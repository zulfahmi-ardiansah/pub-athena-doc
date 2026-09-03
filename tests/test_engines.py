import pytest
from unittest.mock import AsyncMock, MagicMock
from src.config.settings import Settings
from src.engines.factory import create_engine
from src.engines.ocr_hybrid_engine import OcrHybridEngine, LocalCpuEngine
from src.providers.ollama_provider import OllamaProvider


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


def test_ocr_hybrid_engine_tesseract_handles_dict(monkeypatch):
    import io
    from PIL import Image

    # Create dummy 1x1 image bytes
    img = Image.new("RGB", (10, 10), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    dummy_bytes = buf.getvalue()

    engine = OcrHybridEngine(
        llm_provider=MagicMock(),
        ocr_engine_type="tesseract",
    )

    # Mock pytesseract.image_to_string returning a dict
    mock_pytesseract = MagicMock()
    mock_pytesseract.image_to_string.return_value = {"text": "  Extracted Text from Dict  "}
    monkeypatch.setattr("pytesseract.image_to_string", mock_pytesseract.image_to_string)

    result = engine._run_ocr_on_bytes(dummy_bytes)
    assert result == "Extracted Text from Dict"


def test_ocr_hybrid_engine_tesseract_handles_str(monkeypatch):
    import io
    from PIL import Image

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
async def test_ocr_hybrid_engine_warmup():
    mock_provider = AsyncMock()
    mock_provider.preload = AsyncMock(return_value=True)

    engine = OcrHybridEngine(
        llm_provider=mock_provider,
        ocr_engine_type="rapidocr",
    )

    await engine.warmup()
    mock_provider.preload.assert_awaited_once()
