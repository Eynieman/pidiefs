from fastapi import APIRouter, HTTPException

from backend.models.document import QueryRequest, QueryResponse
from backend.services.embeddings import embed_query
from backend.services.vector_store import query_similar, get_document_count
from backend.services.llm import generate_answer
from backend.config import TOP_K_RESULTS, GROQ_API_KEY

router = APIRouter(prefix="/api", tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def query_knowledge_base(request: QueryRequest):
    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY no configurada. Obtén una gratis en https://console.groq.com",
        )

    doc_count = get_document_count()
    if doc_count == 0:
        raise HTTPException(
            status_code=400,
            detail="No hay documentos indexados. Sube un PDF primero.",
        )

    query_embedding = embed_query(request.question)
    top_k = min(request.top_k, TOP_K_RESULTS)
    similar_docs = query_similar(query_embedding, top_k=top_k)

    if not similar_docs:
        return QueryResponse(
            answer="No encontré información relevante para tu pregunta.",
            sources=[],
        )

    answer = generate_answer(request.question, similar_docs)

    sources = [
        {
            "content": doc["content"][:300] + "..." if len(doc["content"]) > 300 else doc["content"],
            "source": doc["metadata"].get("source", "desconocido"),
            "page": doc["metadata"].get("page", 0),
            "score": round(doc["score"], 3),
        }
        for doc in similar_docs
    ]

    return QueryResponse(answer=answer, sources=sources)


@router.get("/health")
async def health_check():
    from backend.config import GROQ_API_KEY

    return {
        "status": "ok",
        "groq_configured": bool(GROQ_API_KEY),
        "documents_indexed": get_document_count(),
    }
