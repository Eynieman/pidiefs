import json

import groq
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.models.document import QueryRequest, QueryResponse
from backend.services.embeddings import embed_query
from backend.services.vector_store import query_similar, get_document_count
from backend.services.llm import generate_answer, generate_answer_stream
from backend.config import TOP_K_RESULTS, GROQ_API_KEY

router = APIRouter(prefix="/api", tags=["query"])


def _build_sources(similar_docs: list[dict]) -> list[dict]:
    return [
        {
            "content": doc["content"][:300] + "..." if len(doc["content"]) > 300 else doc["content"],
            "source": doc["metadata"].get("source", "desconocido"),
            "page": doc["metadata"].get("page", 0),
            "score": round(doc["score"], 3),
        }
        for doc in similar_docs
    ]


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

    query_embedding = await embed_query(request.question)
    top_k = min(request.top_k, TOP_K_RESULTS)
    similar_docs = query_similar(query_embedding, top_k=top_k, doc_id=request.doc_id)

    if not similar_docs:
        return QueryResponse(
            answer="No encontré información relevante para tu pregunta.",
            sources=[],
        )

    try:
        answer = generate_answer(request.question, similar_docs)
    except HTTPException:
        raise
    except groq.RateLimitError:
        raise HTTPException(status_code=429, detail="Límite de solicitudes alcanzado. Intenta más tarde.")
    except groq.AuthenticationError:
        raise HTTPException(status_code=501, detail="Error de autenticación con Groq API.")
    except groq.APIError as e:
        raise HTTPException(status_code=502, detail=f"Error del servicio Groq: {e.message}")

    sources = _build_sources(similar_docs)
    return QueryResponse(answer=answer, sources=sources)


@router.post("/query/stream")
async def query_knowledge_base_stream(request: QueryRequest):
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

    query_embedding = await embed_query(request.question)
    top_k = min(request.top_k, TOP_K_RESULTS)
    similar_docs = query_similar(query_embedding, top_k=top_k, doc_id=request.doc_id)

    if not similar_docs:
        async def empty():
            yield f"data: {json.dumps({'type': 'sources', 'sources': []})}\n\n"
            yield f"data: {json.dumps({'type': 'token', 'content': 'No encontré información relevante para tu pregunta.'})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(empty(), media_type="text/event-stream")

    sources = _build_sources(similar_docs)

    async def stream():
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
        try:
            for token in generate_answer_stream(request.question, similar_docs):
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
        except groq.RateLimitError:
            yield f"data: {json.dumps({'type': 'error', 'content': 'Límite de solicitudes alcanzado'})}\n\n"
        except groq.AuthenticationError:
            yield f"data: {json.dumps({'type': 'error', 'content': 'Error de autenticación con Groq'})}\n\n"
        except groq.APIError as e:
            yield f"data: {json.dumps({'type': 'error', 'content': f'Error de Groq: {e.message}'})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "groq_configured": bool(GROQ_API_KEY),
        "documents_indexed": get_document_count(),
    }
