from abc import ABC, abstractmethod
from typing import Any, Dict
from src.domain.base import BaseDocument


class BaseTextAnalyzer(ABC):
    """Abstract interface for text and document analysis modules."""

    name: str

    @abstractmethod
    async def analyze(
        self,
        input_data: Any,
        document: BaseDocument,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Analyzes input (raw extracted text or rendered image pages) for a target document
        and returns a validated dictionary matching document schema.
        """
        pass
