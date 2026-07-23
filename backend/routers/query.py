import json
import os
import re

import groq
import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

import logging

from backend.models.document import QueryRequest, QueryResponse
from backend.services.embeddings import embed_query
from backend.services.vector_store import query_similar, get_document_count
from backend.services.llm import generate_answer, generate_answer_stream, generate_followups
from backend.services.guardrails import validate_llm_input
from backend.services.query_classifier import classify_query, get_retrieval_strategy
from backend.config import TOP_K_RESULTS, GROQ_API_KEY
from backend.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["query"])

MAX_QUESTION_LENGTH = 2000
DOC_ID_PATTERN = re.compile(r"^[a-f0-9]{12}$")

CALLMEBOT_API_KEY = os.getenv("CALLMEBOT_API_KEY", "")
WHATSAPP_TO_NUMBER = os.getenv("WHATSAPP_TO_NUMBER", "")


def _validate_query_request(query_request: QueryRequest) -> None:
    question = query_request.question.strip()
    query_request.question = question

    if not question:
        raise HTTPException(
            status_code=400,
            detail="La pregunta no puede estar vacia",
        )

    if len(question) > MAX_QUESTION_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"La pregunta excede el limite de {MAX_QUESTION_LENGTH} caracteres",
        )

    if any(ord(c) < 0x20 and c not in ("\n", "\t", "\r") for c in question):
        raise HTTPException(
            status_code=400,
            detail="La pregunta contiene caracteres de control no permitidos",
        )

    if query_request.doc_id and not DOC_ID_PATTERN.match(query_request.doc_id):
        raise HTTPException(
            status_code=400,
            detail="ID de documento invalido",
        )

    if query_request.doc_ids:
        for did in query_request.doc_ids:
            if not DOC_ID_PATTERN.match(did):
                raise HTTPException(
                    status_code=400,
                    detail=f"ID de documento invalido: {did}",
                )

    if question in ("", "...", "?"):
        raise HTTPException(
            status_code=400,
            detail="Pregunta invalida",
        )

    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY no configurada. Obtén una gratis en https://console.groq.com",
        )

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


async def _retrieve_with_fallback(
    question: str,
    embedding: list[float],
    strategy: dict,
    doc_id: str | None = None,
    doc_ids: list[str] | None = None,
) -> tuple[list[dict], str]:
    levels = strategy["levels"]
    top_k = strategy["top_k"]
    docs = query_similar(
        embedding,
        top_k=top_k,
        doc_id=doc_id,
        doc_ids=doc_ids,
        query_text=question,
        abstraction_levels=levels,
    )

    if not docs and levels != [0]:
        logger.info("Retrieval vacío con levels=%s, fallback a local", levels)
        docs = query_similar(
            embedding,
            top_k=5,
            doc_id=doc_id,
            doc_ids=doc_ids,
            query_text=question,
            abstraction_levels=[0],
        )
        return docs, "local"

    return docs, strategy.get("prompt_key", "local")


def _build_sources(similar_docs: list[dict], query_type: str = "local") -> list[dict]:
    return [
        {
            "content": doc["content"][:300] + "..." if len(doc["content"]) > 300 else doc["content"],
            "source": doc["metadata"].get("source", "desconocido"),
            "page": doc["metadata"].get("page", 0),
            "score": round(doc["score"], 3),
            "abstraction_level": doc["metadata"].get("abstraction_level", 0),
            "cluster_topic": doc["metadata"].get("cluster_topic", ""),
        }
        for doc in similar_docs
    ]


@router.post("/query", response_model=QueryResponse)
@limiter.limit("10/minute")
async def query_knowledge_base(request: Request, query_request: QueryRequest):
    _validate_query_request(query_request)

    query_type = query_request.query_type or "auto"
    if query_type == "auto":
        classification = classify_query(query_request.question)
        query_type = classification["type"]
        logger.info("Query classified as '%s' (confidence: %.2f, method: %s)",
                     query_type, classification.get("confidence", 0), classification.get("method", "unknown"))

    strategy = get_retrieval_strategy(query_type)

    query_embedding = await embed_query(query_request.question)
    similar_docs, prompt_type = await _retrieve_with_fallback(
        question=query_request.question,
        embedding=query_embedding,
        strategy=strategy,
        doc_id=query_request.doc_id,
        doc_ids=query_request.doc_ids,
    )

    if not similar_docs:
        return QueryResponse(
            answer="No encontre informacion relevante para tu pregunta.",
            sources=[],
            query_type=query_type,
        )

    try:
        answer = generate_answer(query_request.question, similar_docs, prompt_type)
    except HTTPException:
        raise
    except groq.RateLimitError:
        raise HTTPException(status_code=429, detail="Limite de solicitudes alcanzado. Intenta mas tarde.")
    except groq.AuthenticationError:
        raise HTTPException(status_code=501, detail="Error de autenticacion con Groq API.")
    except groq.APIError as e:
        raise HTTPException(status_code=502, detail=f"Error del servicio Groq: {e.message}")

    sources = _build_sources(similar_docs, query_type)
    return QueryResponse(answer=answer, sources=sources, query_type=query_type)


@router.post("/query/stream")
@limiter.limit("5/minute")
async def query_knowledge_base_stream(request: Request, query_request: QueryRequest):
    _validate_query_request(query_request)

    query_type = query_request.query_type or "auto"
    if query_type == "auto":
        classification = classify_query(query_request.question)
        query_type = classification["type"]
        logger.info("Query classified as '%s' (confidence: %.2f, method: %s)",
                     query_type, classification.get("confidence", 0), classification.get("method", "unknown"))

    strategy = get_retrieval_strategy(query_type)

    query_embedding = await embed_query(query_request.question)
    similar_docs, prompt_type = await _retrieve_with_fallback(
        question=query_request.question,
        embedding=query_embedding,
        strategy=strategy,
        doc_id=query_request.doc_id,
        doc_ids=query_request.doc_ids,
    )

    if not similar_docs:
        async def empty():
            yield f"data: {json.dumps({'type': 'sources', 'sources': [], 'query_type': query_type})}\n\n"
            yield f"data: {json.dumps({'type': 'token', 'content': 'No encontre informacion relevante para tu pregunta.'})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(empty(), media_type="text/event-stream")

    sources = _build_sources(similar_docs, query_type)

    async def stream():
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources, 'query_type': query_type})}\n\n"
        full_answer = ""
        try:
            for token in generate_answer_stream(query_request.question, similar_docs, prompt_type):
                full_answer += token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
        except groq.RateLimitError:
            yield f"data: {json.dumps({'type': 'error', 'content': 'Limite de solicitudes alcanzado'})}\n\n"
        except groq.AuthenticationError:
            yield f"data: {json.dumps({'type': 'error', 'content': 'Error de autenticacion con Groq'})}\n\n"
        except groq.APIError as e:
            yield f"data: {json.dumps({'type': 'error', 'content': f'Error de Groq: {e.message}'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': f'Error inesperado: {str(e)}'})}\n\n"

        if full_answer:
            followups = generate_followups(query_request.question, full_answer)
            if followups:
                yield f"data: {json.dumps({'type': 'followups', 'followups': followups})}\n\n"

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


@router.get("/health/whatsapp")
@limiter.limit("10/minute")
async def whatsapp_health(request: Request):
    if not all([CALLMEBOT_API_KEY, WHATSAPP_TO_NUMBER]):
        return {
            "configured": False,
            "error": "Falta CALLMEBOT_API_KEY o WHATSAPP_TO_NUMBER en .env",
        }

    try:
        url = "https://api.callmebot.com/whatsapp.php"
        params = {
            "phone": WHATSAPP_TO_NUMBER,
            "text": "🧪 Prueba de notificación desde pageyn",
            "apikey": CALLMEBOT_API_KEY,
        }
        response = httpx.get(url, params=params, timeout=10)
        response.raise_for_status()
        return {
            "configured": True,
            "working": True,
        }
    except httpx.HTTPStatusError as e:
        return {
            "configured": True,
            "working": False,
            "error": f"CallMeBot API error {e.response.status_code}: {e.response.text}",
        }
    except Exception as e:
        return {
            "configured": True,
            "working": False,
            "error": str(e),
        }
