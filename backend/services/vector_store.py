import chromadb
from langchain_core.documents import Document
from backend.config import CHROMA_DIR
from backend.services.embeddings import embed_texts
from backend.database import bm25_search

_client = None
_collection = None


def get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = _client.get_or_create_collection(
            name="pdf_knowledge_base",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


async def add_documents(documents: list[Document], doc_id: str) -> int:
    collection = get_collection()

    texts = [doc.page_content for doc in documents]
    embeddings = await embed_texts(texts)

    ids = [f"{doc_id}_chunk_{i}" for i in range(len(documents))]
    metadatas = [
        {
            "source": doc.metadata.get("source", ""),
            "page": doc.metadata.get("page", 0),
            "doc_id": doc_id,
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


def _reciprocal_rank_fusion(results_list: list[list[dict]], k: int = 60) -> list[dict]:
    fused_scores: dict[str, float] = {}
    doc_map: dict[str, dict] = {}

    for results in results_list:
        for rank, doc in enumerate(results):
            key = f"{doc['metadata'].get('doc_id', '')}:{doc['content'][:100]}"
            fused_scores[key] = fused_scores.get(key, 0) + 1.0 / (k + rank + 1)
            doc_map[key] = doc

    sorted_keys = sorted(fused_scores.keys(), key=lambda k: fused_scores[k], reverse=True)
    return [{**doc_map[key], "score": fused_scores[key]} for key in sorted_keys]


def query_similar(
    query_embedding: list[float],
    top_k: int = 5,
    doc_id: str | None = None,
    doc_ids: list[str] | None = None,
    query_text: str | None = None,
) -> list[dict]:
    collection = get_collection()

    if doc_ids:
        where = {"doc_id": {"$in": doc_ids}}
    elif doc_id:
        where = {"doc_id": doc_id}
    else:
        where = None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k * 2,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    vector_docs = []
    if results["documents"] and results["documents"][0]:
        for i, text in enumerate(results["documents"][0]):
            vector_docs.append(
                {
                    "content": text,
                    "metadata": results["metadatas"][0][i],
                    "score": 1 - results["distances"][0][i],
                }
            )

    if query_text:
        bm25_docs = bm25_search(query_text, top_k=top_k * 2, doc_ids=doc_ids)
        if vector_docs and bm25_docs:
            fused = _reciprocal_rank_fusion([vector_docs, bm25_docs])
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
    collection = get_collection()
    results = collection.get(include=["metadatas"])
    if not results["metadatas"]:
        return 0
    doc_ids = {m.get("doc_id") for m in results["metadatas"]}
    return len(doc_ids)
