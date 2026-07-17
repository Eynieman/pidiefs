from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import documents, query

app = FastAPI(
    title="Pidiefs — PDF Knowledge Base",
    description="RAG pipeline para consultar PDFs con embeddings y LLM",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)

app.include_router(documents.router)
app.include_router(query.router)


@app.get("/")
async def root():
    return {
        "name": "Pidiefs API",
        "version": "1.0.0",
        "docs": "/docs",
    }
