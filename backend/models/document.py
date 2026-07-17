from pydantic import BaseModel
from datetime import datetime


class DocumentResponse(BaseModel):
    id: str
    filename: str
    pages: int
    chunks: int
    uploaded_at: str
    duplicate_of: str | None = None
    summary: str | None = None


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    doc_id: str | None = None
    doc_ids: list[str] | None = None


class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]


class HealthResponse(BaseModel):
    status: str
    groq_configured: bool
    documents_indexed: int


class StatsResponse(BaseModel):
    total_documents: int
    total_pages: int
    total_chunks: int
    last_upload: str | None
