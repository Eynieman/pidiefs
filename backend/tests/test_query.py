import groq
import pytest
from unittest.mock import MagicMock, AsyncMock


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


async def test_query_rate_limit(client, monkeypatch):
    monkeypatch.setattr("backend.routers.query.get_document_count", lambda: 1)
    monkeypatch.setattr(
        "backend.routers.query.embed_query",
        AsyncMock(return_value=[0.1] * 384),
    )
    monkeypatch.setattr(
        "backend.routers.query.query_similar",
        lambda emb, top_k, doc_id=None, doc_ids=None, query_text=None, abstraction_levels=None: [{"content": "test", "metadata": {"source": "a", "page": 1, "abstraction_level": 0}, "score": 0.9}],
    )

    def mock_generate(question, docs, query_type="local"):
        raise groq.RateLimitError(
            message="rate limited",
            response=MagicMock(status_code=429),
            body=None,
        )

    monkeypatch.setattr("backend.routers.query.generate_answer", mock_generate)

    res = await client.post(
        "/api/query",
        json={"question": "test question"},
    )
    assert res.status_code == 429


async def test_query_auth_error(client, monkeypatch):
    monkeypatch.setattr("backend.routers.query.get_document_count", lambda: 1)
    monkeypatch.setattr(
        "backend.routers.query.embed_query",
        AsyncMock(return_value=[0.1] * 384),
    )
    monkeypatch.setattr(
        "backend.routers.query.query_similar",
        lambda emb, top_k, doc_id=None, doc_ids=None, query_text=None, abstraction_levels=None: [{"content": "test", "metadata": {"source": "a", "page": 1, "abstraction_level": 0}, "score": 0.9}],
    )

    def mock_generate(question, docs, query_type="local"):
        raise groq.AuthenticationError(
            message="invalid key",
            response=MagicMock(status_code=401),
            body=None,
        )

    monkeypatch.setattr("backend.routers.query.generate_answer", mock_generate)

    res = await client.post(
        "/api/query",
        json={"question": "test question"},
    )
    assert res.status_code == 501
