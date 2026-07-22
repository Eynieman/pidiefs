import logging

import chromadb
from chromadb.config import Settings
from langchain_core.documents import Document
from backend.config import CHROMA_DIR
from backend.services.embeddings import embed_texts
from backend.database import bm25_search

logger = logging.getLogger(__name__)

_client = None
_collection = None


def get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(
            name="pdf_knowledge_base",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


async def add_documents(documents: list[Document], doc_id: str, abstraction_level: int = 0) -> int:
    collection = get_collection()

    texts = [doc.page_content for doc in documents]
    embeddings = await embed_texts(texts)

    ids = [f"{doc_id}_chunk_{i}_lvl{abstraction_level}" for i in range(len(documents))]
    metadatas = [
        {
            "source": doc.metadata.get("source", ""),
            "page": doc.metadata.get("page", 0),
            "doc_id": doc_id,
            "abstraction_level": abstraction_level,
            "cluster_topic": doc.metadata.get("cluster_topic", ""),
        }
        for doc in documents
    ]

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    return len(ids)


async def add_summary_documents(summaries: list[dict], doc_id: str, abstraction_level: int = 1) -> int:
    collection = get_collection()

    texts = [s["content"] for s in summaries]
    embeddings = await embed_texts(texts)

    ids = [f"{doc_id}_summary_{i}_lvl{abstraction_level}" for i in range(len(summaries))]
    metadatas = [
        {
            "source": s.get("source", ""),
            "page": 0,
            "doc_id": doc_id,
            "abstraction_level": abstraction_level,
            "cluster_topic": s.get("title", ""),
        }
        for s in summaries
    ]

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    return len(ids)


def _reciprocal_rank_fusion(
    results_list: list[list[dict]],
    k: int = 60,
    weights: list[float] | None = None,
) -> list[dict]:
    fused_scores: dict[str, float] = {}
    doc_map: dict[str, dict] = {}

    weights = weights or [1.0] * len(results_list)

    for weight, results in zip(weights, results_list):
        for rank, doc in enumerate(results):
            key = f"{doc['metadata'].get('doc_id', '')}:{doc.get('content', '')[:100]}"
            fused_scores[key] = fused_scores.get(key, 0) + weight / (k + rank + 1)
            doc_map[key] = doc

    sorted_keys = sorted(fused_scores.keys(), key=lambda key: fused_scores[key], reverse=True)
    return [{**doc_map[key], "score": fused_scores[key]} for key in sorted_keys]


def query_similar(
    query_embedding: list[float],
    top_k: int = 5,
    doc_id: str | None = None,
    doc_ids: list[str] | None = None,
    query_text: str | None = None,
    abstraction_levels: list[int] | None = None,
    bm25_weight: float = 0.5,
) -> list[dict]:
    collection = get_collection()

    conditions: list[dict] = []
    if doc_ids:
        conditions.append({"doc_id": {"$in": doc_ids}})
    elif doc_id:
        conditions.append({"doc_id": doc_id})
    if abstraction_levels is not None and abstraction_levels != [0]:
        conditions.append({"abstraction_level": {"$in": abstraction_levels}})

    where: dict | None = None
    if len(conditions) > 1:
        where = {"$and": conditions}
    elif len(conditions) == 1:
        where = conditions[0]

    n_results = top_k * 2
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    vector_docs = []
    if results["documents"] and results["documents"][0]:
        for i, text in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i]
            vector_docs.append(
                {
                    "content": text,
                    "metadata": meta,
                    "score": 1 - results["distances"][0][i],
                }
            )

    if query_text:
        bm25_docs = bm25_search(query_text, top_k=top_k * 2, doc_ids=doc_ids)
        if vector_docs and bm25_docs:
            fused = _reciprocal_rank_fusion(
                [vector_docs, bm25_docs],
                weights=[1.0, bm25_weight],
            )
            return fused[:top_k]
        elif bm25_docs:
            return bm25_docs[:top_k]

    return vector_docs[:top_k]


def delete_document(doc_id: str) -> int:
    collection = get_collection()

    results = collection.get(where={"doc_id": doc_id})
    if results["ids"]:
        collection.delete(ids=results["ids"])
    return len(results["ids"])


def get_document_count() -> int:
    from backend.database import load_metadata
    return len(load_metadata())
