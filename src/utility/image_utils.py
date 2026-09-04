import io
import logging
from typing import Any, Dict, Optional, Tuple
import numpy as np
import cv2
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)


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


def deskew_image(
    img: np.ndarray,
    min_angle: float = 0.5,
    max_angle: float = 45.0
) -> Tuple[np.ndarray, float]:
    """
    Detects text orientation/skew angle and rotates image to deskew it.
    Returns (deskewed_np_array, detected_skew_angle).
    """
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if len(img.shape) == 3 else img.copy()
        # Invert foreground text to white on black background for contour detection
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        pts = cv2.findNonZero(thresh)
        if pts is None or len(pts) < 50:
            return img, 0.0

        rect = cv2.minAreaRect(pts)
        angle = rect[-1]

        # Normalize angle convention: OpenCV minAreaRect returns angle in [-90, 0)
        if angle < -45.0:
            angle = -(90.0 + angle)
        else:
            angle = -angle

        if min_angle <= abs(angle) <= max_angle:
            h, w = img.shape[:2]
            center = (w // 2, h // 2)
            matrix = cv2.getRotationMatrix2D(center, -angle, 1.0)
            border_val = (255, 255, 255) if len(img.shape) == 3 else 255
            rotated = cv2.warpAffine(
                img,
                matrix,
                (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=border_val
            )
            return rotated, float(round(angle, 2))

        return img, 0.0
    except Exception as err:
        logger.warning(f"Deskew failed, falling back to original image: {err}")
        return img, 0.0


def whiten_background_and_enhance(
    img: np.ndarray,
    denoise_strength: int = 5,
    white_cutoff: int = 230,
    black_level: int = 25,
    gamma: float = 1.15,
    sharpen_strength: float = 1.15
) -> np.ndarray:
    """
    Suppresses wavy background textures, removes color casts & shadow gradients,
    flattens background to pure white, and deepens text characters without overexposing midtones.
    """
    try:
        is_gray = (len(img.shape) == 2)
        h, w = img.shape[:2]

        # 1. Edge-preserving bilateral filter to smooth out low-amplitude wavy textures
        if denoise_strength > 0:
            denoised = cv2.bilateralFilter(img, d=denoise_strength, sigmaColor=50, sigmaSpace=50)
        else:
            denoised = img

        channels = [denoised] if is_gray else cv2.split(denoised)
        out_channels = []

        # Adaptive kernel dimensions
        k_size = max(31, int(min(h, w) * 0.10)) | 1
        dilate_k = max(5, int(min(h, w) * 0.02)) | 1

        for ch in channels:
            ch_bg_global = float(np.percentile(ch, 75))

            # Dilate to eliminate thin text strokes from background estimate
            dilated = cv2.dilate(ch, cv2.getStructuringElement(cv2.MORPH_RECT, (dilate_k, dilate_k)))
            local_bg = cv2.GaussianBlur(dilated, (k_size, k_size), 0).astype(np.float32)

            # Floor background to 75% of global background to protect large dark regions (hair, photo, headers)
            safe_bg = np.maximum(local_bg, ch_bg_global * 0.75)

            # 2. Illumination division normalization
            divided = np.clip((ch.astype(np.float32) / np.maximum(safe_bg, 1.0)) * 255.0, 0, 255)

            # 3. Balanced level stretch (prevents overexposure and blown-out highlights)
            norm = np.clip((divided - float(black_level)) / max(1.0, float(white_cutoff - black_level)), 0.0, 1.0)

            # 4. Gamma curve (gamma > 1.0 maintains rich midtones and deepens text)
            if gamma != 1.0:
                norm = np.power(norm, gamma)

            stretched = (norm * 255.0).astype(np.uint8)
            out_channels.append(stretched)

        merged = out_channels[0] if is_gray else cv2.merge(out_channels)

        # 5. Controlled text sharpening
        if sharpen_strength > 1.0:
            blurred = cv2.GaussianBlur(merged, (0, 0), 1.5)
            sharpened = cv2.addWeighted(merged, sharpen_strength, blurred, -(sharpen_strength - 1.0), 0)
            return np.clip(sharpened, 0, 255).astype(np.uint8)
        return merged
    except Exception as err:
        logger.warning(f"Document enhancement failed, falling back: {err}")
        return img


def enhance_contrast(
    img: np.ndarray,
    clip_limit: float = 2.0,
    tile_grid_size: Tuple[int, int] = (8, 8)
) -> np.ndarray:
    """
    Enhances contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).
    Handles both grayscale and RGB images.
    """
    try:
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        if len(img.shape) == 2:
            return clahe.apply(img)
        elif len(img.shape) == 3:
            lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
            l_channel, a_channel, b_channel = cv2.split(lab)
            l_enhanced = clahe.apply(l_channel)
            enhanced_lab = cv2.merge((l_enhanced, a_channel, b_channel))
            return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2RGB)
        return img
    except Exception as err:
        logger.warning(f"Contrast enhancement failed, falling back to original image: {err}")
        return img


def apply_threshold(img: np.ndarray, mode: str = "otsu") -> np.ndarray:
    """
    Applies image binarization / thresholding.
    Supported modes: 'otsu', 'adaptive'.
    """
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if len(img.shape) == 3 else img.copy()
        mode_lower = (mode or "").lower()

        if mode_lower == "otsu":
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return thresh
        elif mode_lower == "adaptive":
            blurred = cv2.medianBlur(gray, 3)
            return cv2.adaptiveThreshold(
                blurred,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                21,
                10
            )
        return img
    except Exception as err:
        logger.warning(f"Thresholding ({mode}) failed, falling back to original image: {err}")
        return img


def preprocess_image_bytes(
    image_bytes: bytes,
    deskew: bool = True,
    enhance_contrast_enabled: bool = True,
    threshold_mode: Optional[str] = "none",
    gamma: float = 1.15,
    white_cutoff: int = 230,
    black_level: int = 25
) -> Tuple[bytes, Dict[str, Any]]:
    """
    Full image preprocessing pipeline for OCR:
    1. EXIF orientation correction.
    2. Color space normalization (RGB/Grayscale).
    3. Deskewing / skew angle compensation.
    4. Edge-preserving wave suppression, background whitening, and character sharpening.
    5. Optional thresholding / binarization ('otsu' | 'adaptive' | 'none').

    Returns (preprocessed_png_bytes, preprocessing_metadata).
    """
    with Image.open(io.BytesIO(image_bytes)) as img_pil:
        img_pil = ImageOps.exif_transpose(img_pil)
        if img_pil.mode not in ("RGB", "L"):
            img_pil = img_pil.convert("RGB")

        orig_dims = (img_pil.width, img_pil.height)
        img_np = np.array(img_pil)

    meta: Dict[str, Any] = {
        "original_dims": orig_dims,
        "deskew_applied": False,
        "deskew_angle": 0.0,
        "whitened_applied": False,
        "contrast_enhanced": False,
        "threshold_mode": threshold_mode or "none",
        "images": {}
    }

    # 1. Deskew
    if deskew:
        img_np, angle = deskew_image(img_np)
        if abs(angle) > 0.0:
            meta["deskew_applied"] = True
            meta["deskew_angle"] = angle
            deskew_buf = io.BytesIO()
            Image.fromarray(img_np).save(deskew_buf, format="PNG")
            meta["images"]["deskewed"] = deskew_buf.getvalue()

    # 2. Document Background Whitening, Wave Suppression & Character Sharpening
    if enhance_contrast_enabled:
        img_np = whiten_background_and_enhance(
            img_np,
            gamma=gamma,
            white_cutoff=white_cutoff,
            black_level=black_level
        )
        meta["whitened_applied"] = True
        meta["contrast_enhanced"] = True
        whitened_buf = io.BytesIO()
        Image.fromarray(img_np).save(whitened_buf, format="PNG")
        meta["images"]["whitened"] = whitened_buf.getvalue()
        meta["images"]["contrast_enhanced"] = whitened_buf.getvalue()

    # 3. Thresholding
    thresh_mode = (threshold_mode or "none").lower()
    if thresh_mode not in ("none", ""):
        img_np = apply_threshold(img_np, mode=thresh_mode)
        thresh_buf = io.BytesIO()
        Image.fromarray(img_np).save(thresh_buf, format="PNG")
        meta["images"]["thresholded"] = thresh_buf.getvalue()

    out_pil = Image.fromarray(img_np)
    meta["processed_dims"] = (out_pil.width, out_pil.height)

    out_buffer = io.BytesIO()
    out_pil.save(out_buffer, format="PNG")
    final_bytes = out_buffer.getvalue()
    meta["images"]["preprocessed"] = final_bytes

    return final_bytes, meta


def normalize_image_bytes(image_bytes: bytes) -> Tuple[bytes, Tuple[int, int]]:
    """
    Normalizes image:
    1. Fixes EXIF orientation transpose.
    2. Converts to RGB if CMYK or RGBA.
    3. Returns (normalized_png_bytes, (width, height)).
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        dims = (img.width, img.height)
        out_buffer = io.BytesIO()
        img.save(out_buffer, format="PNG")
        return out_buffer.getvalue(), dims
