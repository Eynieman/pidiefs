from backend.services.cache import (
    llm_answer_cache,
    make_llm_key,
    make_embedding_key,
    make_followup_key,
    make_summary_key,
)


def test_make_llm_key_deterministic():
    llm_answer_cache.clear()
    docs = [{"content": "test", "metadata": {"source": "a", "page": 1}}]
    key1 = make_llm_key("pregunta", docs, "local")
    key2 = make_llm_key("pregunta", docs, "local")
    assert key1 == key2


def test_make_llm_key_differs_for_different_inputs():
    llm_answer_cache.clear()
    docs = [{"content": "test", "metadata": {"source": "a", "page": 1}}]
    key1 = make_llm_key("pregunta", docs, "local")
    key2 = make_llm_key("otra pregunta", docs, "local")
    assert key1 != key2


def test_cache_stores_and_retrieves():
    llm_answer_cache.clear()
    docs = [{"content": "data", "metadata": {"source": "b", "page": 2}}]
    key = make_llm_key("q", docs, "local")
    llm_answer_cache[key] = "respuesta cacheada"
    assert llm_answer_cache.get(key) == "respuesta cacheada"


def test_cache_miss_returns_none():
    llm_answer_cache.clear()
    docs = [{"content": "data", "metadata": {"source": "c", "page": 3}}]
    key = make_llm_key("q", docs, "local")
    assert llm_answer_cache.get(key) is None


def test_embedding_key_uniqueness():
    key1 = make_embedding_key("misma query")
    key2 = make_embedding_key("misma query")
    assert key1 == key2

    key3 = make_embedding_key("different query")
    assert key1 != key3


def test_followup_key_deterministic():
    key1 = make_followup_key("pregunta", "respuesta")
    key2 = make_followup_key("pregunta", "respuesta")
    assert key1 == key2


def test_summary_key_deterministic():
    key1 = make_summary_key("doc.pdf", "contenido del pdf")
    key2 = make_summary_key("doc.pdf", "contenido del pdf")
    assert key1 == key2
