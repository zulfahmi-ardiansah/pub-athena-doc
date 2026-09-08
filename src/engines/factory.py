import logging
from typing import Dict
from src.config.settings import Settings
from src.engines.base import BaseExtractionEngine
from src.engines.string_engine import StringEngine
from src.engines.visual_engine import VisualEngine
from src.engines.hybrid_engine import HybridEngine
from src.modules.preprocessors.base import BaseImagePreprocessor
from src.modules.extractors.base import BaseTextExtractor
from src.modules.analyzers.base import BaseTextAnalyzer
from src.modules.preprocessors.image_preprocessor import ImagePreprocessor
from src.modules.extractors.digital_pdf import DigitalPdfExtractor
from src.modules.extractors.ocr_extractor import OcrExtractor
from src.modules.extractors.visual_llm_extractor import VisualLlmExtractor
from src.modules.analyzers.string_analyzer import StringTextAnalyzer
from src.modules.analyzers.llm_analyzer import LlmTextAnalyzer
from src.modules.analyzers.visual_llm_analyzer import VisualLlmAnalyzer
from src.providers.base import BaseLLMProvider
from src.providers.ollama_provider import OllamaProvider
from src.providers.google_provider import GoogleGenAIProvider

logger = logging.getLogger(__name__)


def create_llm_provider(settings: Settings, is_vision: bool = False) -> BaseLLMProvider:
    """Helper to instantiate configured LLM provider (Ollama or Google Gemini)."""
    provider_type = settings.get_vision_provider_type() if is_vision else settings.get_text_provider_type()
    provider_type = (provider_type or "ollama").lower()

    if provider_type == "google":
        model_name = settings.google_vision_model if is_vision else settings.google_text_model
        return GoogleGenAIProvider(
            api_key=settings.google_api_key,
            project_id=settings.google_project_id,
            location=settings.google_location,
            credentials_file=settings.google_application_credentials,
            model=model_name,
        )

    # Default to Ollama
    model_name = settings.ollama_vision_model if is_vision else settings.ollama_text_model
    return OllamaProvider(
        base_url=settings.ollama_base_url,
        model=model_name,
        timeout_seconds=settings.ollama_timeout_seconds,
        keep_alive=settings.ollama_keep_alive,
    )


def create_engine(settings: Settings) -> BaseExtractionEngine:
    """Factory creating configured extraction engine backend and pluggable modules."""
    engine_type = (settings.engine_type or "hybrid_engine").lower()

    # 1. Initialize Common Preprocessor
    preprocessor = ImagePreprocessor(
        enabled=settings.image_preprocess,
        deskew=settings.image_deskew,
        enhance_contrast=settings.image_enhance_contrast,
        threshold_mode=settings.image_threshold_mode,
        gamma=settings.image_enhance_gamma,
        white_cutoff=settings.image_enhance_white_cutoff,
        black_level=settings.image_enhance_black_level,
        render_dpi=settings.image_render_dpi,
    )

    if engine_type == "string_engine":
        logger.info(f"Initializing StringEngine with OCR backend '{settings.ocr_backend}'...")
        digital_extractor = DigitalPdfExtractor()
        ocr_extractor = OcrExtractor(
            backend=settings.ocr_backend,
            tesseract_cmd=settings.tesseract_cmd or None,
            google_api_key=settings.google_api_key or None,
            google_project_id=settings.google_project_id or None,
            google_credentials=settings.google_application_credentials or None,
            preprocessor=preprocessor,
        )
        string_analyzer = StringTextAnalyzer()
        return StringEngine(
            digital_extractor=digital_extractor,
            ocr_extractor=ocr_extractor,
            analyzer=string_analyzer,
            preprocessor=preprocessor,
            min_confidence=settings.extraction_min_confidence,
        )

    elif engine_type == "visual_engine":
        vision_provider_type = settings.get_vision_provider_type()
        logger.info(f"Initializing VisualEngine with Vision LLM provider '{vision_provider_type}'...")
        vision_provider = create_llm_provider(settings, is_vision=True)
        visual_analyzer = VisualLlmAnalyzer(vision_provider=vision_provider)
        return VisualEngine(
            analyzer=visual_analyzer,
            preprocessor=preprocessor,
        )

    elif engine_type == "hybrid_engine":
        text_provider_type = settings.get_text_provider_type()
        vision_provider_type = settings.get_vision_provider_type()
        logger.info(
            f"Initializing HybridEngine with pipeline '{settings.extraction_pipeline}', "
            f"text LLM provider '{text_provider_type}', vision LLM provider '{vision_provider_type}', "
            f"and analysis mode '{settings.analysis_mode}'..."
        )
        text_provider = create_llm_provider(settings, is_vision=False)
        vision_provider = create_llm_provider(settings, is_vision=True)

        extractors: Dict[str, BaseTextExtractor] = {
            "digital_pdf": DigitalPdfExtractor(),
            "ocr": OcrExtractor(
                backend=settings.ocr_backend,
                tesseract_cmd=settings.tesseract_cmd or None,
                google_api_key=settings.google_api_key or None,
                google_project_id=settings.google_project_id or None,
                google_credentials=settings.google_application_credentials or None,
                preprocessor=preprocessor,
            ),
            "visual_llm": VisualLlmExtractor(
                vision_provider=vision_provider,
                preprocessor=preprocessor,
            ),
        }

        analyzers: Dict[str, BaseTextAnalyzer] = {
            "llm": LlmTextAnalyzer(llm_provider=text_provider),
            "string": StringTextAnalyzer(),
        }

        return HybridEngine(
            extractors=extractors,
            analyzers=analyzers,
            preprocessor=preprocessor,
            pipeline=settings.get_extraction_stages(),
            min_confidence=settings.extraction_min_confidence,
            analysis_mode=settings.analysis_mode,
        )

    else:
        raise ValueError(f"Unknown ENGINE_TYPE: '{settings.engine_type}'")
