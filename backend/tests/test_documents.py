import io

import pytest


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


async def test_list_documents_empty(client):
    res = await client.get("/api/documents")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


async def test_upload_invalid_extension(client):
    csv_content = b"col1,col2\na,b"
    res = await client.post(
        "/api/documents",
        files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 400
    assert "PDF" in res.json()["detail"]


async def test_upload_valid_pdf(client):
    res = await client.post(
        "/api/documents",
        files={"file": ("test.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["filename"] == "test.pdf"
    assert "id" in data


async def test_upload_then_list(client):
    upload_res = await client.post(
        "/api/documents",
        files={"file": ("list_test.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
    )
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["id"]

    list_res = await client.get("/api/documents")
    assert list_res.status_code == 200
    docs = list_res.json()
    assert any(d["id"] == doc_id for d in docs)

    del_res = await client.delete(f"/api/documents/{doc_id}")
    assert del_res.status_code == 200


async def test_delete_nonexistent(client):
    res = await client.delete("/api/documents/nonexistent_id")
    assert res.status_code == 404


async def test_stats_empty(client):
    res = await client.get("/api/documents/stats")
    assert res.status_code == 200
    data = res.json()
    assert "total_documents" in data
    assert "total_pages" in data
    assert "total_chunks" in data
    assert "last_upload" in data


async def test_stats_after_upload(client):
    upload_res = await client.post(
        "/api/documents",
        files={"file": ("stats_test.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
    )
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["id"]

    stats_res = await client.get("/api/documents/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_documents"] >= 1
    assert stats["total_pages"] >= 1
    assert stats["total_chunks"] >= 1
    assert stats["last_upload"] is not None

    await client.delete(f"/api/documents/{doc_id}")


async def test_upload_duplicate_returns_duplicate_of(client):
    unique_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 3 3]/Parent 2 0 R"
        b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        b"4 0 obj<</Length 48>>stream\n"
        b"BT /F1 1 Tf (Unique Duplicate Test) Tj ET\nendstream\nendobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000270 00000 n \n"
        b"0000000368 00000 n \n"
        b"trailer<</Size 6/Root 1 0 R>>\n"
        b"startxref\n461\n%%EOF"
    )

    res1 = await client.post(
        "/api/documents",
        files={"file": ("dup_test.pdf", io.BytesIO(unique_pdf), "application/pdf")},
    )
    assert res1.status_code == 200
    doc_id1 = res1.json()["id"]

    res2 = await client.post(
        "/api/documents",
        files={"file": ("dup_test.pdf", io.BytesIO(unique_pdf), "application/pdf")},
    )
    assert res2.status_code == 200
    assert res2.json()["duplicate_of"] == doc_id1

    await client.delete(f"/api/documents/{doc_id1}")
    await client.delete(f"/api/documents/{res2.json()['id']}")


async def test_upload_empty_file(client):
    res = await client.post(
        "/api/documents",
        files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
    )
    assert res.status_code == 400
    assert "vacio" in res.json()["detail"].lower()


async def test_upload_exceeds_size_limit(client):
    large_content = b"%PDF-1.4\n" + b"0" * (50 * 1024 * 1024 + 1)
    res = await client.post(
        "/api/documents",
        files={"file": ("large.pdf", io.BytesIO(large_content), "application/pdf")},
    )
    assert res.status_code == 413
    assert "excede" in res.json()["detail"].lower() or "limite" in res.json()["detail"].lower()
