import io
from typing import Optional, Tuple
from PIL import Image, ImageOps


def is_image(content_type: Optional[str], filename: Optional[str] = None) -> bool:
    """Check if file is supported image format."""
    if content_type:
        ct = content_type.lower()
        if any(img_type in ct for img_type in ["image/jpeg", "image/png", "image/webp", "image/bmp", "image/tiff"]):
            return True
    if filename:
        fn = filename.lower()
        if any(fn.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"]):
            return True
    return False


def normalize_image_bytes(image_bytes: bytes) -> Tuple[bytes, Tuple[int, int]]:
    """
    Normalizes image:
    1. Fixes EXIF orientation transpose.
    2. Converts to RGB if CMYK or RGBA.
    3. Returns (normalized_png_bytes, (width, height)).
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        # Auto-rotate according to EXIF
        img = ImageOps.exif_transpose(img)

        # Convert to RGB mode if necessary
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        dims = (img.width, img.height)
        out_buffer = io.BytesIO()
        img.save(out_buffer, format="PNG")
        return out_buffer.getvalue(), dims
