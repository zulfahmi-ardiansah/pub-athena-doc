import io
from PIL import Image
from src.utility.image_utils import is_image, normalize_image_bytes
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
