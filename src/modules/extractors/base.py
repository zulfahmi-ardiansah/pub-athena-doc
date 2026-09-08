from abc import ABC, abstractmethod
from typing import Any, Optional
from src.modules.base import ExtractionOutput


class BaseTextExtractor(ABC):
    """Abstract interface for text extraction modules."""

    name: str

    @abstractmethod
    async def extract_text(
        self,
        file_bytes: bytes,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        **kwargs: Any,
    ) -> ExtractionOutput:
        """
        Extracts raw text from input bytes (PDF or Image) and computes a confidence score (0.0 to 1.0).
        """
        pass
