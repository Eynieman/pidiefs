from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.routers import documents, query
from backend.services.embeddings import preload_model

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    preload_model()
    yield


app = FastAPI(
    title="Pidiefs — PDF Knowledge Base",
    description="RAG pipeline para consultar PDFs con embeddings y LLM",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
