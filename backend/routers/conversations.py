import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.rate_limit import limiter
from backend.database import (
    create_conversation,
    get_conversations,
    get_conversation,
    delete_conversation,
    add_chat_message,
    get_chat_messages,
    load_metadata,
)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class CreateConversationRequest(BaseModel):
    doc_ids: list[str]
    title: str | None = None


class AddMessageRequest(BaseModel):
    role: str
    content: str
    sources: list[dict] | None = None


@router.get("")
@limiter.limit("60/minute")
async def list_conversations(request: Request):
    return get_conversations()


@router.post("")
@limiter.limit("30/minute")
async def create_new_conversation(request: Request, body: CreateConversationRequest):
    if body.doc_ids:
        metadata = load_metadata()
        invalid_ids = [doc_id for doc_id in body.doc_ids if doc_id not in metadata]
        if invalid_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Documentos no encontrados: {', '.join(invalid_ids)}",
            )
    conversation_id = uuid.uuid4().hex[:12]
    conv = create_conversation(conversation_id, body.doc_ids, body.title)
    return conv


@router.get("/{conversation_id}")
@limiter.limit("60/minute")
async def get_conversation_detail(request: Request, conversation_id: str):
    conv = get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    messages = get_chat_messages(conversation_id)
    return {**conv, "messages": messages}


@router.delete("/{conversation_id}")
@limiter.limit("20/minute")
async def delete_conversation_endpoint(request: Request, conversation_id: str):
    deleted = delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    return {"deleted": True}


@router.post("/{conversation_id}/messages")
@limiter.limit("60/minute")
async def add_message(request: Request, conversation_id: str, body: AddMessageRequest):
    conv = get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    msg = add_chat_message(conversation_id, body.role, body.content, body.sources)
    return msg


@router.get("/{conversation_id}/messages")
@limiter.limit("60/minute")
async def list_messages(request: Request, conversation_id: str):
    conv = get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    return get_chat_messages(conversation_id)
