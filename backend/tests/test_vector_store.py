import pytest
from langchain_core.documents import Document
from backend.services.vector_store import (
    add_documents,
    query_similar,
    delete_document,
    get_document_count,
)


@pytest.mark.asyncio
async def test_add_documents_returns_count():
    docs = [
        Document(page_content="Hello world", metadata={"source": "test.pdf", "page": 1}),
    ]
    count = await add_documents(docs, "test_doc_001")
    assert count == 1


@pytest.mark.asyncio
async def test_query_similar_returns_results():
    docs = [
        Document(page_content="Python programming language", metadata={"source": "test.pdf", "page": 1}),
    ]
    await add_documents(docs, "test_doc_002")

    from backend.services.embeddings import embed_query
    embedding = await embed_query("Python")
    results = query_similar(embedding, top_k=1)
    assert len(results) > 0
    assert "content" in results[0]
    assert "score" in results[0]


@pytest.mark.asyncio
async def test_delete_document_removes_chunks():
    docs = [
        Document(page_content="To be deleted", metadata={"source": "test.pdf", "page": 1}),
    ]
    await add_documents(docs, "test_doc_003")

    deleted = delete_document("test_doc_003")
    assert deleted > 0

    from backend.services.embeddings import embed_query
    embedding = await embed_query("deleted")
    results = query_similar(embedding, top_k=5, doc_id="test_doc_003")
    assert len(results) == 0
