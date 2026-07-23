import asyncio
import logging
from sentence_transformers import SentenceTransformer
from backend.config import EMBEDDING_MODEL
from backend.services.cache import query_embedding_cache, make_embedding_key

logger = logging.getLogger(__name__)

_model = None


def preload_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        preload_model()
    return _model


async def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_model()
    embeddings = await asyncio.to_thread(model.encode, texts, show_progress_bar=False)
    return embeddings.tolist()


async def embed_query(query: str) -> list[float]:
    key = make_embedding_key(query)
    cached = query_embedding_cache.get(key)
    if cached is not None:
        logger.info("Cache hit for embed_query: %s", query[:50])
        return cached
    model = get_model()
    embedding = await asyncio.to_thread(model.encode, [query], show_progress_bar=False)
    result = embedding[0].tolist()
    query_embedding_cache[key] = result
    return result
