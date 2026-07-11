import pdfplumber
from pypdf import PdfReader
from pathlib import Path


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

    return {
        "filename": path.name,
        "total_pages": len(reader.pages),
        "extracted_pages": len(pages),
        "pages": pages,
    }
