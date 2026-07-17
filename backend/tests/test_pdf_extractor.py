import io
from pathlib import Path
from backend.services.pdf_extractor import extract_text


MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 3 3]/Parent 2 0 R"
    b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
    b"4 0 obj<</Length 44>>stream\n"
    b"BT /F1 1 Tf (Hello World) Tj ET\nendstream\nendobj\n"
    b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"xref\n0 6\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"0000000266 00000 n \n"
    b"0000000360 00000 n \n"
    b"trailer<</Size 6/Root 1 0 R>>\n"
    b"startxref\n457\n%%EOF"
)


def test_extract_text_returns_structure(tmp_path):
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(MINIMAL_PDF)
    result = extract_text(pdf_path)
    assert "pages" in result
    assert "total_pages" in result
    assert "extracted_pages" in result
    assert isinstance(result["pages"], list)


def test_extract_text_total_pages(tmp_path):
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(MINIMAL_PDF)
    result = extract_text(pdf_path)
    assert result["total_pages"] == 1
