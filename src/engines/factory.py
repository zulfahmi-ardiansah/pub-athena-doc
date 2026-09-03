import logging
from src.config.settings import Settings
from src.engines.base import BaseExtractionEngine
from src.engines.ocr_hybrid_engine import OcrHybridEngine
from src.engines.cloud_google_engine import CloudGoogleEngine
from src.providers.ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)


def create_engine(settings: Settings) -> BaseExtractionEngine:
    """Factory creating configured extraction engine backend."""
    backend = settings.engine_backend.lower()

    if backend in ("ocr_hybrid", "local_cpu"):
        logger.info(
            f"Initializing OcrHybridEngine with Ollama ({settings.ollama_model}) "
            f"and OCR ({settings.ocr_engine})..."
        )
        ollama_provider = OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout_seconds=settings.ollama_timeout_seconds,
            keep_alive=settings.ollama_keep_alive,
        )
        return OcrHybridEngine(
            llm_provider=ollama_provider,
            ocr_engine_type=settings.ocr_engine,
            tesseract_cmd=settings.tesseract_cmd or None,
        )

    elif backend == "cloud_google":
        logger.info(f"Initializing CloudGoogleEngine with Gemini ({settings.gemini_model})...")
        return CloudGoogleEngine(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
        )

    else:
        raise ValueError(f"Unknown ENGINE_BACKEND: {settings.engine_backend}")
