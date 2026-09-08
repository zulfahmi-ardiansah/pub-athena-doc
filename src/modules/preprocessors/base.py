from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from src.modules.base import PreprocessResult


class BaseImagePreprocessor(ABC):
    """Abstract interface for image preprocessing modules."""

    @abstractmethod
    def preprocess(self, image_bytes: bytes) -> PreprocessResult:
        """Applies configured preprocessing transformations (deskew, contrast, thresholding)."""
        pass

    @abstractmethod
    def render_pdf_to_images(self, pdf_bytes: bytes, dpi: Optional[int] = None) -> List[bytes]:
        """Renders every page of a PDF into high-res PNG image bytes."""
        pass

    @abstractmethod
    def normalize_image(self, image_bytes: bytes) -> Tuple[bytes, Tuple[int, int]]:
        """Ensures image is in valid RGB PNG format and returns (normalized_bytes, dimensions)."""
        pass
