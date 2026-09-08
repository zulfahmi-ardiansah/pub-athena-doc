import logging
from typing import List, Optional, Tuple
import fitz  # PyMuPDF
from src.modules.base import PreprocessResult
from src.modules.preprocessors.base import BaseImagePreprocessor
from src.utility.image_utils import normalize_image_bytes, preprocess_image_bytes

logger = logging.getLogger(__name__)


class ImagePreprocessor(BaseImagePreprocessor):
    """
    Decoupled Image Preprocessor module:
    Handles deskewing, CLAHE/gamma contrast enhancement, thresholding, and PDF page rendering.
    """

    def __init__(
        self,
        enabled: bool = True,
        deskew: bool = True,
        enhance_contrast: bool = True,
        threshold_mode: Optional[str] = "none",
        gamma: float = 1.15,
        white_cutoff: int = 230,
        black_level: int = 25,
        render_dpi: int = 150,
    ) -> None:
        self.enabled = enabled
        self.deskew = deskew
        self.enhance_contrast = enhance_contrast
        self.threshold_mode = threshold_mode or "none"
        self.gamma = gamma
        self.white_cutoff = white_cutoff
        self.black_level = black_level
        self.render_dpi = render_dpi

    def preprocess(self, image_bytes: bytes) -> PreprocessResult:
        if not self.enabled:
            return PreprocessResult(
                processed_bytes=image_bytes,
                metadata={"preprocessing_enabled": False}
            )

        processed_bytes, meta = preprocess_image_bytes(
            image_bytes=image_bytes,
            deskew=self.deskew,
            enhance_contrast_enabled=self.enhance_contrast,
            threshold_mode=self.threshold_mode,
            gamma=self.gamma,
            white_cutoff=self.white_cutoff,
            black_level=self.black_level
        )
        return PreprocessResult(processed_bytes=processed_bytes, metadata=meta)

    def normalize_image(self, image_bytes: bytes) -> Tuple[bytes, Tuple[int, int]]:
        return normalize_image_bytes(image_bytes)

    def render_pdf_to_images(self, pdf_bytes: bytes, dpi: Optional[int] = None) -> List[bytes]:
        target_dpi = dpi or self.render_dpi
        image_list: List[bytes] = []
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            zoom = target_dpi / 72.0
            matrix = fitz.Matrix(zoom, zoom)
            for page in doc:
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                image_list.append(pix.tobytes("png"))
        finally:
            doc.close()
        return image_list
