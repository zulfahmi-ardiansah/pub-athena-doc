from functools import lru_cache
from src.config.settings import get_settings
from src.domain.registry import DocumentRegistry, get_document_registry
from src.engines.base import BaseExtractionEngine
from src.engines.factory import create_engine


@lru_cache()
def get_engine_singleton() -> BaseExtractionEngine:
    """Cached singleton instance of the configured extraction engine."""
    settings = get_settings()
    return create_engine(settings)


def get_registry() -> DocumentRegistry:
    """Provides the document registry."""
    return get_document_registry()
