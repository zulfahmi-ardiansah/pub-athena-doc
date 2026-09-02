from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from src.domain.base import BaseDocument


class BaseExtractionEngine(ABC):
    """Abstract interface for document extraction backends."""

    name: str

    @abstractmethod
    async def extract(
        self,
        file_bytes: bytes,
        filename: Optional[str],
        content_type: Optional[str],
        document: BaseDocument
    ) -> Dict[str, Any]:
        """
        Processes input file bytes (PDF or Image), extracts text/features,
        executes structured LLM inference, and returns validated schema dictionary.
        """
        pass
