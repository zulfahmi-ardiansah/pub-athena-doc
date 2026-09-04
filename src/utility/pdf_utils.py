from typing import List, Tuple, Optional, cast
import fitz  # PyMuPDF


def is_pdf(content_type: Optional[str], filename: Optional[str] = None) -> bool:
    """Check if uploaded file is a PDF based on content-type or filename extension."""
    if content_type and "pdf" in content_type.lower():
        return True
    if filename and filename.lower().endswith(".pdf"):
        return True
    return False


def inspect_and_extract_pdf_pages(
    pdf_bytes: bytes,
    min_digital_char_count: int = 30,
    render_dpi: int = 200
) -> List[Tuple[int, Optional[str], Optional[bytes]]]:
    """
    Processes multi-page PDF bytes and inspects each page:
    Returns list of tuples: (page_number_1_indexed, digital_text_or_None, rendered_png_bytes_or_None)

    If page has digital text >= min_digital_char_count, digital_text is populated.
    If page is scanned/image-only, rendered_png_bytes is populated.
    """
    results: List[Tuple[int, Optional[str], Optional[bytes]]] = []
    
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        for page_idx in range(len(doc)):
            page_num = page_idx + 1
            page = doc[page_idx]
            text = cast(str, page.get_text("text")).strip()

            if len(text) >= min_digital_char_count:
                results.append((page_num, text, None))
            else:
                # Render scanned page to high-res PNG pixmap
                zoom = render_dpi / 72.0
                matrix = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                png_bytes = pix.tobytes("png")
                results.append((page_num, None, png_bytes))
    finally:
        doc.close()

    return results
