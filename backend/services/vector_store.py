import chromadb
from langchain_core.documents import Document
from backend.config import CHROMA_DIR
from backend.services.embeddings import embed_texts

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


def query_similar(query_embedding: list[float], top_k: int = 5, doc_id: str | None = None) -> list[dict]:
    collection = get_collection()

    where = {"doc_id": doc_id} if doc_id else None
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    docs = []
    if results["documents"] and results["documents"][0]:
        for i, text in enumerate(results["documents"][0]):
            docs.append(
                {
                    "content": text,
                    "metadata": results["metadatas"][0][i],
                    "score": 1 - results["distances"][0][i],
                }
            )
    return docs


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
