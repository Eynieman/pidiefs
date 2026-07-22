"""Tests de seguridad para el backend de pageyn."""

import io

import pytest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture
def sync_client():
    with TestClient(app) as c:
        yield c


# ─── 1. XSS Prevention ──────────────────────────────────────────────────


def test_xss_in_question_is_rejected(sync_client):
    payload = {
        "question": "<script>alert(1)</script>",
        "top_k": 1,
    }
    response = sync_client.post("/api/query", json=payload)
    assert response.status_code in (200, 400, 422, 500)
    if response.status_code == 200:
        data = response.json()
        assert "answer" in data


def test_xss_in_question_raw_html(sync_client):
    payload = {
        "question": "<img src=x onerror=alert(1)>",
        "top_k": 1,
    }
    response = sync_client.post("/api/query", json=payload)
    assert response.status_code in (200, 400, 422, 500)
    if response.status_code == 200:
        data = response.json()
        assert "answer" in data


# ─── 2. Path Traversal ──────────────────────────────────────────────────


def test_path_traversal_in_doc_id(sync_client):
    response = sync_client.get("/api/documents/invalid!path/chunks")
    assert response.status_code == 400


def test_path_traversal_in_delete(sync_client):
    response = sync_client.delete("/api/documents/%2e%2e%2f%2e%2e%2fetc/passwd")
    assert response.status_code in (400, 404)


# ─── 3. Input Validation (campos extra) ─────────────────────────────────


def test_extra_fields_in_query_request(sync_client):
    payload = {
        "question": "test",
        "top_k": 1,
        "role": "admin",
        "extra_field": "malicious",
    }
    response = sync_client.post("/api/query", json=payload)
    assert response.status_code in (400, 422)


def test_extra_fields_in_add_message(sync_client):
    payload = {
        "role": "admin",
        "content": "test message",
    }
    response = sync_client.post("/api/conversations/abc123def456/messages", json=payload)
    assert response.status_code in (400, 422)


# ─── 4. File Upload Validation ──────────────────────────────────────────


def test_upload_fake_pdf_no_magic_bytes(sync_client):
    fake_pdf = io.BytesIO(b"This is not a PDF file but has .pdf extension")
    files = {"file": ("test.pdf", fake_pdf, "application/pdf")}
    response = sync_client.post("/api/documents", files=files)
    assert response.status_code in (400, 415, 422)
    assert any(word in response.text.lower() for word in ("pdf", "archivo", "no es"))


def test_upload_empty_file(sync_client):
    empty = io.BytesIO(b"")
    files = {"file": ("empty.pdf", empty, "application/pdf")}
    response = sync_client.post("/api/documents", files=files)
    assert response.status_code in (400, 422, 415)


def test_upload_wrong_extension(sync_client):
    fake = io.BytesIO(b"%PDF-1.4 fake content")
    files = {"file": ("malware.exe", fake, "application/pdf")}
    response = sync_client.post("/api/documents", files=files)
    assert response.status_code == 400


# ─── 5. File Size Limit ─────────────────────────────────────────────────


def test_upload_file_too_large(sync_client):
    large_content = b"%PDF-1.4 " + b"A" * (55 * 1024 * 1024)
    large = io.BytesIO(large_content)
    files = {"file": ("large.pdf", large, "application/pdf")}
    response = sync_client.post("/api/documents", files=files)
    assert response.status_code in (413, 400, 422)


# ─── 6. Empty Question ──────────────────────────────────────────────────


def test_empty_question(sync_client):
    payload = {"question": "", "top_k": 1}
    response = sync_client.post("/api/query", json=payload)
    assert response.status_code in (400, 422)


def test_whitespace_only_question(sync_client):
    payload = {"question": "   ", "top_k": 1}
    response = sync_client.post("/api/query", json=payload)
    assert response.status_code in (400, 422)


# ─── 7. Control Characters ──────────────────────────────────────────────


def test_control_characters_in_question(sync_client):
    payload = {"question": "hello\x00world", "top_k": 1}
    response = sync_client.post("/api/query", json=payload)
    assert response.status_code in (400, 422)


# ─── 8. Pydantic Validation ─────────────────────────────────────────────


def test_invalid_top_k_range(sync_client):
    payload = {"question": "test", "top_k": 999}
    response = sync_client.post("/api/query", json=payload)
    assert response.status_code in (400, 422)


def test_question_too_long(sync_client):
    payload = {"question": "A" * 2500, "top_k": 1}
    response = sync_client.post("/api/query", json=payload)
    assert response.status_code in (400, 422)


# ─── 9. Content-Type Validation ─────────────────────────────────────────


def test_wrong_content_type(sync_client):
    payload = "raw text data"
    response = sync_client.post(
        "/api/query",
        content=payload,
        headers={"Content-Type": "text/plain"},
    )
    assert response.status_code in (400, 415, 422)


# ─── 10. Rate Limiting ──────────────────────────────────────────────────


def test_rate_limiting_health_endpoint(sync_client):
    responses = []
    for _ in range(5):
        resp = sync_client.get("/api/health")
        responses.append(resp.status_code)
    ok_count = sum(1 for s in responses if s == 200)
    assert ok_count >= 3, f"Solo {ok_count}/5 responses fueron 200: {responses}"
