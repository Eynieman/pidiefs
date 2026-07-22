import json
import re

import groq
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

import logging

from backend.models.document import QueryRequest, QueryResponse
from backend.services.embeddings import embed_query
from backend.services.vector_store import query_similar, get_document_count
from backend.services.llm import generate_answer, generate_answer_stream
from backend.services.guardrails import validate_llm_input
from backend.config import TOP_K_RESULTS, GROQ_API_KEY
from backend.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["query"])

MAX_QUESTION_LENGTH = 2000
DOC_ID_PATTERN = re.compile(r"^[a-f0-9]{12}$")


def _validate_query_request(query_request: QueryRequest) -> None:
    question = query_request.question.strip()
    query_request.question = question

    if not question:
        raise HTTPException(
            status_code=400,
            detail="La pregunta no puede estar vacía",
        )

    if len(question) > MAX_QUESTION_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"La pregunta excede el límite de {MAX_QUESTION_LENGTH} caracteres",
        )

    if any(ord(c) < 0x20 and c not in ("\n", "\t", "\r") for c in question):
        raise HTTPException(
            status_code=400,
            detail="La pregunta contiene caracteres de control no permitidos",
        )

    if query_request.doc_id and not DOC_ID_PATTERN.match(query_request.doc_id):
        raise HTTPException(
            status_code=400,
            detail="ID de documento inválido",
        )

    if query_request.doc_ids:
        for did in query_request.doc_ids:
            if not DOC_ID_PATTERN.match(did):
                raise HTTPException(
                    status_code=400,
                    detail=f"ID de documento inválido: {did}",
                )

    if question in ("", "...", "?"):
        raise HTTPException(
            status_code=400,
            detail="Pregunta inválida",
        )

    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY no configurada. Obtén una gratis en https://console.groq.com",
        )

    # Input guardrails
    input_result = validate_llm_input(question)
    if not input_result["safe"]:
        if input_result.get("has_pii"):
            logger.warning("PII detectado en pregunta (aceptada): %s", question[:100])
        else:
            jailbreak_reasons = [r for r in input_result["reasons"] if r != "pii_detected"]
            if jailbreak_reasons:
                raise HTTPException(
                    status_code=400,
                    detail="La pregunta contiene contenido no permitido",
                )

    doc_count = get_document_count()
    if doc_count == 0:
        raise HTTPException(
            status_code=400,
            detail="No hay documentos indexados. Sube un PDF primero.",
        )


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
@limiter.limit("10/minute")
async def query_knowledge_base(request: Request, query_request: QueryRequest):
    _validate_query_request(query_request)

    query_embedding = await embed_query(query_request.question)
    top_k = min(query_request.top_k, TOP_K_RESULTS)
    similar_docs = query_similar(
        query_embedding,
        top_k=top_k,
        doc_id=query_request.doc_id,
        doc_ids=query_request.doc_ids,
        query_text=query_request.question,
    )

    if not similar_docs:
        return QueryResponse(
            answer="No encontré información relevante para tu pregunta.",
            sources=[],
        )

    try:
        answer = generate_answer(query_request.question, similar_docs)
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
@limiter.limit("5/minute")
async def query_knowledge_base_stream(request: Request, query_request: QueryRequest):
    _validate_query_request(query_request)

    query_embedding = await embed_query(query_request.question)
    top_k = min(query_request.top_k, TOP_K_RESULTS)
    similar_docs = query_similar(
        query_embedding,
        top_k=top_k,
        doc_id=query_request.doc_id,
        doc_ids=query_request.doc_ids,
        query_text=query_request.question,
    )

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
            for token in generate_answer_stream(query_request.question, similar_docs):
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
        except groq.RateLimitError:
            yield f"data: {json.dumps({'type': 'error', 'content': 'Límite de solicitudes alcanzado'})}\n\n"
        except groq.AuthenticationError:
            yield f"data: {json.dumps({'type': 'error', 'content': 'Error de autenticación con Groq'})}\n\n"
        except groq.APIError as e:
            yield f"data: {json.dumps({'type': 'error', 'content': f'Error de Groq: {e.message}'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': f'Error inesperado: {str(e)}'})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/health")
@limiter.limit("60/minute")
async def health_check(request: Request):
    return {
        "status": "ok",
        "groq_configured": bool(GROQ_API_KEY),
        "documents_indexed": get_document_count(),
    }
