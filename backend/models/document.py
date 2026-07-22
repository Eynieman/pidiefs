from pydantic import BaseModel, Field
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
    question: str = Field(max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    doc_id: str | None = None
    doc_ids: list[str] | None = None

    model_config = {"extra": "forbid"}


class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]


class BatchDeleteRequest(BaseModel):
    doc_ids: list[str]

    model_config = {"extra": "forbid"}


class HealthResponse(BaseModel):
    status: str
    groq_configured: bool
    documents_indexed: int


class StatsResponse(BaseModel):
    total_documents: int
    total_pages: int
    total_chunks: int
    last_upload: str | None
