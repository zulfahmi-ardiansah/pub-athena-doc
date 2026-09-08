from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ExtractionOutput:
    """Standardized output returned by all text extraction modules."""
    text: str
    confidence: float
    stage_name: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not bool(self.text and self.text.strip())


@dataclass
class PreprocessResult:
    """Standardized output from image preprocessing."""
    processed_bytes: bytes
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PageExtractionResult:
    """Encapsulates page-level extraction result with metadata."""
    page_num: int
    output: ExtractionOutput
    preprocess_metadata: Optional[Dict[str, Any]] = None
