from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional
from src.domain.base import BaseDocument


@dataclass
class ExtractionResult:
    data: Dict[str, Any]
    trace: Optional[Dict[str, Any]] = None


class ExtractionError(Exception):
    """Exception raised when document extraction fails, holding partial execution trace."""

    def __init__(
        self,
        message: str,
        trace: Optional[Dict[str, Any]] = None,
        raw_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.trace = trace
        self.raw_data = raw_data


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
