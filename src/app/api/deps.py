from functools import lru_cache
from fastapi import Depends
from src.config.settings import Settings, get_settings
from src.domain.registry import DocumentRegistry, get_document_registry
from src.engines.base import BaseExtractionEngine
from src.engines.factory import create_engine


@lru_cache()
def get_engine_singleton(settings: Settings = Depends(get_settings)) -> BaseExtractionEngine:
    """Cached singleton instance of the configured extraction engine."""
    return create_engine(settings)


def get_registry() -> DocumentRegistry:
    """Provides the document registry."""
    return get_document_registry()
