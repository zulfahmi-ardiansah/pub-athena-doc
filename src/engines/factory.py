import logging
from src.config.settings import Settings
from src.engines.base import BaseExtractionEngine
from src.engines.local_cpu_engine import LocalCpuEngine
from src.engines.cloud_google_engine import CloudGoogleEngine
from src.providers.ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)


def create_engine(settings: Settings) -> BaseExtractionEngine:
    """Factory creating configured extraction engine backend."""
    backend = settings.engine_backend.lower()

    if backend == "local_cpu":
        logger.info(f"Initializing LocalCpuEngine with Ollama ({settings.ollama_model})...")
        ollama_provider = OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout_seconds=settings.ollama_timeout_seconds,
        )
        return LocalCpuEngine(llm_provider=ollama_provider)

    elif backend == "cloud_google":
        logger.info(f"Initializing CloudGoogleEngine with Gemini ({settings.gemini_model})...")
        return CloudGoogleEngine(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
        )

    else:
        raise ValueError(f"Unknown ENGINE_BACKEND: {settings.engine_backend}")
