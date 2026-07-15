import io


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
    minimal_pdf = (
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
    res = await client.post(
        "/api/documents",
        files={"file": ("test.pdf", io.BytesIO(minimal_pdf), "application/pdf")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["filename"] == "test.pdf"
    assert "id" in data


async def test_upload_then_list(client):
    minimal_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 3 3]/Parent 2 0 R"
        b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        b"4 0 obj<</Length 44>>stream\n"
        b"BT /F1 1 Tf (Test) Tj ET\nendstream\nendobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000266 00000 n \n"
        b"0000000340 00000 n \n"
        b"trailer<</Size 6/Root 1 0 R>>\n"
        b"startxref\n427\n%%EOF"
    )
    upload_res = await client.post(
        "/api/documents",
        files={"file": ("list_test.pdf", io.BytesIO(minimal_pdf), "application/pdf")},
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
