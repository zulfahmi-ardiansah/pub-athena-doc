from abc import ABC, abstractmethod
from typing import Any, Dict, Type
from pydantic import BaseModel


class BaseDocument(ABC):
    """Abstract base class representing a document extraction specification."""

    slug: str
    name: str
    description: str
    schema_class: Type[BaseModel]

    def get_json_schema(self) -> Dict[str, Any]:
        """Returns JSON schema for structured LLM generation."""
        return self.schema_class.model_json_schema()

    @abstractmethod
    def build_system_prompt(self) -> str:
        """Returns system prompt defining extraction rules and context."""
        pass

    @abstractmethod
    def build_user_prompt(self, raw_text: str) -> str:
        """Returns user prompt with injected OCR/raw text."""
        pass

    def validate_payload(self, data: Dict[str, Any]) -> BaseModel:
        """Validates and parses raw dictionary into typed Pydantic schema."""
        return self.schema_class.model_validate(data)
