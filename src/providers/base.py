from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseLLMProvider(ABC):
    """Abstract interface for structured JSON LLM generation."""

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        json_schema: Dict[str, Any],
        system_prompt: str = "",
        images: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Executes LLM completion constrained by a JSON Schema.
        Optionally accepts base64-encoded image strings for vision/multimodal models.
        Returns parsed JSON object as a Python dictionary.
        """
        pass

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str = "",
        images: Optional[List[str]] = None,
    ) -> str:
        """
        Executes unconstrained text generation (e.g. for vision OCR transcription).
        """
        raise NotImplementedError("generate_text is not implemented for this provider.")

    async def preload(self) -> bool:
        """Optional preload / warmup step for the LLM provider."""
        return True

