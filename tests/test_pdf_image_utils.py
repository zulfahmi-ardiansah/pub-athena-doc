import io
import numpy as np
import cv2
from PIL import Image
from src.utility.image_utils import (
    is_image,
    normalize_image_bytes,
    deskew_image,
    whiten_background_and_enhance,
    enhance_contrast,
    apply_threshold,
    preprocess_image_bytes
)
from src.utility.pdf_utils import is_pdf


def test_is_pdf():
    assert is_pdf("application/pdf", "doc.pdf") is True
    assert is_pdf(None, "doc.pdf") is True
    assert is_pdf("image/png", "doc.png") is False


def test_is_image():
    assert is_image("image/jpeg", "photo.jpg") is True
    assert is_image("image/png", "photo.png") is True
    assert is_image(None, "photo.webp") is True
    assert is_image("application/pdf", "file.pdf") is False


def test_normalize_image_bytes():
    # Create simple 10x10 in-memory image
    img = Image.new("RGB", (10, 10), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    raw_bytes = buf.getvalue()

    norm_bytes, dims = normalize_image_bytes(raw_bytes)
    assert dims == (10, 10)
    assert len(norm_bytes) > 0


def test_deskew_image_recovers_angle():
    # Create synthetic white image with dark text
    img = np.full((300, 500, 3), 255, dtype=np.uint8)
    cv2.putText(img, "ATHENA OCR TEST DOCUMENT TEXT", (40, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    # Rotate 10 degrees clockwise
    center = (250, 150)
    matrix = cv2.getRotationMatrix2D(center, 10.0, 1.0)
    rotated = cv2.warpAffine(img, matrix, (500, 300), borderValue=(255, 255, 255))

    deskewed, detected_angle = deskew_image(rotated)
    assert abs(detected_angle - 10.0) < 1.5
    assert deskewed.shape == rotated.shape


def test_deskew_image_ignores_minimal_angle():
    img = np.full((100, 200, 3), 255, dtype=np.uint8)
    deskewed, angle = deskew_image(img, min_angle=0.5)
    assert angle == 0.0
    assert deskewed.shape == img.shape


def test_enhance_contrast_rgb_and_gray():
    # RGB
    rgb = np.random.randint(50, 150, (100, 100, 3), dtype=np.uint8)
    enhanced_rgb = enhance_contrast(rgb)
    assert enhanced_rgb.shape == rgb.shape

    # Grayscale
    gray = np.random.randint(50, 150, (100, 100), dtype=np.uint8)
    enhanced_gray = enhance_contrast(gray)
    assert enhanced_gray.shape == gray.shape


def test_apply_threshold_otsu_and_adaptive():
    img = np.full((100, 100, 3), 200, dtype=np.uint8)
    cv2.putText(img, "TEST", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (30, 30, 30), 2)

    otsu_res = apply_threshold(img, mode="otsu")
    assert len(otsu_res.shape) == 2
    assert set(np.unique(otsu_res)).issubset({0, 255})

    adaptive_res = apply_threshold(img, mode="adaptive")
    assert len(adaptive_res.shape) == 2
    assert set(np.unique(adaptive_res)).issubset({0, 255})

    none_res = apply_threshold(img, mode="none")
    assert none_res.shape == img.shape


def test_preprocess_image_bytes_full_pipeline():
    img = Image.new("RGB", (200, 100), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    raw_bytes = buf.getvalue()

    proc_bytes, meta = preprocess_image_bytes(
        raw_bytes,
        deskew=True,
        enhance_contrast_enabled=True,
        threshold_mode="otsu"
    )

    assert len(proc_bytes) > 0
    assert meta["contrast_enhanced"] is True
    assert meta["threshold_mode"] == "otsu"
    assert meta["original_dims"] == (200, 100)
    assert meta["processed_dims"] == (200, 100)


def test_whiten_background_and_enhance():
    # Synthetic image with colored background and dark text
    img = np.full((300, 500, 3), [215, 195, 175], dtype=np.uint8)
    cv2.putText(img, "PROVINSI DKI JAKARTA", (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (30, 30, 30), 2)

    whitened = whiten_background_and_enhance(img)
    assert whitened.shape == (300, 500, 3)

    # Background should be whitened to >= 250
    assert np.all(whitened[10, 10] >= 250)

    # Find where text was drawn in original image
    ys, xs = np.where(img[:, :, 0] == 30)
    sample_y, sample_x = ys[0], xs[0]

    # Text in whitened result should remain crisp and dark
    assert np.all(whitened[sample_y, sample_x] < 100)
