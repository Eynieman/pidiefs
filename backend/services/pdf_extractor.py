import logging
import pdfplumber
from pypdf import PdfReader
from pathlib import Path

from backend.config import OCR_ENABLED, OCR_LANGUAGE

logger = logging.getLogger(__name__)


def _extract_with_ocr(pdf_path: Path) -> list[dict]:
    try:
        import pytesseract
        from PIL import Image
        import io
    except ImportError:
        logger.warning("pytesseract or Pillow not installed, OCR unavailable")
        return []

    pages = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for i, page in enumerate(pdf.pages):
                img = page.to_image(resolution=300)
                img_bytes = io.BytesIO()
                img.save(img_bytes, format="PNG")
                img_bytes.seek(0)
                pil_image = Image.open(img_bytes)
                text = pytesseract.image_to_string(pil_image, lang=OCR_LANGUAGE)
                if text.strip():
                    pages.append({"page_num": i + 1, "content": text})
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        return []
    return pages


def extract_text(pdf_path: str | Path) -> dict:
    path = Path(pdf_path)
    reader = PdfReader(str(path))
    pages = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append({"page_num": i + 1, "content": text})

    if not pages:
        with pdfplumber.open(str(path)) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append({"page_num": i + 1, "content": text})

    if not pages and OCR_ENABLED:
        logger.info(f"Text extraction empty, attempting OCR for {path.name}")
        pages = _extract_with_ocr(path)

    return {
        "filename": path.name,
        "total_pages": len(reader.pages),
        "extracted_pages": len(pages),
        "pages": pages,
    }
