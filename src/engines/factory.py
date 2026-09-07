import logging
from src.config.settings import Settings
from src.engines.base import BaseExtractionEngine
from src.engines.ocr_hybrid_engine import OcrHybridEngine
from src.engines.visual_model_engine import VisualModelEngine
from src.engines.cloud_google_engine import CloudGoogleEngine
from src.providers.ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)


def create_engine(settings: Settings) -> BaseExtractionEngine:
    """Factory creating configured extraction engine backend."""
    backend = settings.engine_backend.lower()

    if backend in ("ocr_hybrid", "local_cpu"):
        ocr_engine_type = (settings.ocr_engine or "rapidocr").lower()
        logger.info(
            f"Initializing OcrHybridEngine with Ollama ({settings.ollama_model}) "
            f"and OCR ({ocr_engine_type})..."
        )
        ollama_provider = OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout_seconds=settings.ollama_timeout_seconds,
            keep_alive=settings.ollama_keep_alive,
        )
        vision_provider = None
        if ocr_engine_type in ("vision_model", "visual_model", "vision"):
            vision_model_name = settings.ollama_vision_model or settings.ollama_model
            logger.info(f"Configuring Ollama Vision provider ({vision_model_name}) as OCR engine...")
            vision_provider = OllamaProvider(
                base_url=settings.ollama_base_url,
                model=vision_model_name,
                timeout_seconds=settings.ollama_timeout_seconds,
                keep_alive=settings.ollama_keep_alive,
            )
        return OcrHybridEngine(
            llm_provider=ollama_provider,
            vision_provider=vision_provider,
            ocr_engine_type=settings.ocr_engine,
            tesseract_cmd=settings.tesseract_cmd or None,
            preprocess=settings.ocr_preprocess,
            deskew=settings.ocr_deskew,
            enhance_contrast=settings.ocr_enhance_contrast,
            threshold_mode=settings.ocr_threshold_mode,
            gamma=settings.ocr_enhance_gamma,
            white_cutoff=settings.ocr_enhance_white_cutoff,
            black_level=settings.ocr_enhance_black_level,
        )

    elif backend == "visual_model":
        model_name = settings.ollama_vision_model or settings.ollama_model
        logger.info(f"Initializing VisualModelEngine with Ollama Vision model ({model_name})...")
        ollama_provider = OllamaProvider(
            base_url=settings.ollama_base_url,
            model=model_name,
            timeout_seconds=settings.ollama_timeout_seconds,
            keep_alive=settings.ollama_keep_alive,
        )
        return VisualModelEngine(
            llm_provider=ollama_provider,
            preprocess=settings.ocr_preprocess,
            deskew=settings.ocr_deskew,
            enhance_contrast=settings.ocr_enhance_contrast,
            threshold_mode=settings.ocr_threshold_mode,
            gamma=settings.ocr_enhance_gamma,
            white_cutoff=settings.ocr_enhance_white_cutoff,
            black_level=settings.ocr_enhance_black_level,
        )

    elif backend == "cloud_google":
        logger.info(f"Initializing CloudGoogleEngine with Gemini ({settings.gemini_model})...")
        return CloudGoogleEngine(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
        )

    else:
        raise ValueError(f"Unknown ENGINE_BACKEND: {settings.engine_backend}")
