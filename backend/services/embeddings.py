import asyncio
from sentence_transformers import SentenceTransformer
from backend.config import EMBEDDING_MODEL

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
    model = get_model()
    embedding = await asyncio.to_thread(model.encode, [query], show_progress_bar=False)
    return embedding[0].tolist()
