import logging
from typing import Any, Dict
from pydantic import BaseModel
from src.domain.base import BaseDocument
from src.modules.analyzers.base import BaseTextAnalyzer

logger = logging.getLogger(__name__)


class StringTextAnalyzer(BaseTextAnalyzer):
    """
    Zero-LLM deterministic String Text Analyzer.
    Dispatches to document domain string/regex parsers for instantaneous extraction.
    """

    name = "string_analyzer"

    async def analyze(
        self,
        input_data: Any,
        document: BaseDocument,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        raw_text = str(input_data or "").strip()
        if not raw_text:
            raise ValueError("Empty text provided to StringTextAnalyzer")

        parsed = document.parse_string(raw_text)
        if isinstance(parsed, BaseModel):
            return parsed.model_dump()
        elif isinstance(parsed, dict):
            validated = document.validate_payload(parsed)
            return validated.model_dump()
        else:
            raise TypeError(f"Unexpected return type from {document.slug}.parse_string: {type(parsed)}")
