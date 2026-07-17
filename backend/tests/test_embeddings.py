import pytest
from backend.services.embeddings import embed_texts, embed_query


@pytest.mark.asyncio
async def test_embed_texts_returns_list():
    result = await embed_texts(["hello world"])
    assert isinstance(result, list)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_embed_texts_dimensions():
    result = await embed_texts(["test"])
    assert isinstance(result[0], list)
    assert len(result[0]) == 384


@pytest.mark.asyncio
async def test_embed_texts_multiple():
    result = await embed_texts(["hello", "world"])
    assert len(result) == 2


@pytest.mark.asyncio
async def test_embed_query_returns_vector():
    result = await embed_query("test query")
    assert isinstance(result, list)
    assert len(result) == 384
