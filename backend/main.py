import os
import re
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette_csrf import CSRFMiddleware

from backend.rate_limit import limiter
from backend.middleware.audit import AuditMiddleware
from backend.middleware.monitoring import admin_router
from backend.routers import documents, query, conversations
from backend.services.embeddings import preload_model


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

ALLOWED_CONTENT_TYPES = {
    "application/json",
    "multipart/form-data",
    "application/x-www-form-urlencoded",
}

MAX_BODY_SIZE = 55 * 1024 * 1024


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        content_type = request.headers.get("content-type", "").split(";")[0]
        is_multipart = "multipart/form-data" in request.headers.get("content-type", "")
        if not is_multipart and content_type not in ALLOWED_CONTENT_TYPES and content_type:
            return JSONResponse(
                status_code=415,
                content={"detail": "Tipo de contenido no soportado"},
            )

    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_SIZE:
        return JSONResponse(
            status_code=413,
            content={"detail": "El cuerpo de la solicitud excede el límite permitido"},
        )

    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Process-Time"] = str(round(process_time, 4))

    return response


app.add_middleware(AuditMiddleware)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "localhost",
        "127.0.0.1",
        "testserver",
        "test",
        os.getenv("TRUSTED_HOST", ""),
    ],
)

if os.getenv("ENVIRONMENT", "").lower() == "production":
    app.add_middleware(HTTPSRedirectMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)

# CSRF Protection: Double Submit Cookie
# Las rutas /api/ están exentas porque el frontend usa Next.js rewrites (mismo origen)
# y aún no envía tokens CSRF. Para nuevas rutas fuera de /api/ la protección aplica.
CSRF_SECRET = os.getenv("CSRF_SECRET", "dev-csrf-secret-change-in-production")
app.add_middleware(
    CSRFMiddleware,
    secret=CSRF_SECRET,
    header_name="x-csrf-token",
    exempt_urls=[
        re.compile(r"^/api/"),
    ],
    cookie_secure=os.getenv("ENVIRONMENT", "").lower() == "production",
    cookie_samesite="lax",
)

app.include_router(admin_router)
app.include_router(documents.router)
app.include_router(query.router)
app.include_router(conversations.router)


@app.get("/")
async def root():
    return {
        "name": "Pidiefs API",
        "version": "1.0.0",
        "docs": "/docs",
    }
