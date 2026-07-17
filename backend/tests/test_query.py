async def test_health_check(client):
    res = await client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "groq_configured" in data
    assert "documents_indexed" in data


async def test_query_no_documents(client, monkeypatch):
    monkeypatch.setattr("backend.routers.query.get_document_count", lambda: 0)
    res = await client.post(
        "/api/query",
        json={"question": "test question"},
    )
    assert res.status_code == 400
    assert "documentos" in res.json()["detail"].lower()


async def test_query_with_groq_not_configured(client, monkeypatch):
    from backend.routers import query
    monkeypatch.setattr(query, "GROQ_API_KEY", "")

    res = await client.post(
        "/api/query",
        json={"question": "test question"},
    )
    assert res.status_code == 500
    assert "GROQ_API_KEY" in res.json()["detail"]
