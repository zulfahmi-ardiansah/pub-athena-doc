from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional
from src.domain.base import BaseDocument


@dataclass
class ExtractionResult:
    data: Dict[str, Any]
    trace: Optional[Dict[str, Any]] = None


class BaseExtractionEngine(ABC):
    """Abstract interface for document extraction backends."""

    name: str

    @abstractmethod
    async def extract(
        self,
        file_bytes: bytes,
        filename: Optional[str],
        content_type: Optional[str],
        document: BaseDocument,
        trace: bool = False
    ) -> ExtractionResult:
        """
        Processes input file bytes (PDF or Image), extracts text/features,
        executes structured LLM inference, and returns ExtractionResult.
        """
        pass

    async def warmup(self) -> None:
        """Optional engine warmup / model preloading during application startup."""
        pass
