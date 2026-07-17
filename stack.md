# Stack — PDF Knowledge Base (RAG)

Arquitectura de una aplicación web para consultar PDFs mediante un pipeline de Retrieval-Augmented Generation (RAG).

---

## 1. Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js)                       │
│  ┌───────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Upload UI │  │ Chat / Query │  │ Document List / Status   │  │
│  │(drag&drop)│  │ (markdown)   │  │ (thumbnails, batch)      │  │
│  └─────┬─────┘  └──────┬───────┘  └────────────┬─────────────┘  │
└────────┼───────────────┼───────────────────────┼────────────────┘
         │               │                       │
         ▼               ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API REST (FastAPI)                           │
│  POST /upload    POST /query/stream  GET /documents             │
│  GET /stats      GET /chunks         DELETE /documents/batch    │
│  DELETE /doc     POST /conversations GET /conversations         │
└────┬───────────────┬───────────────────┬────────────────────────┘
     │               │                   │
     ▼               ▼                   ▼
┌─────────────┐ ┌──────────────┐ ┌──────────────────────────────┐
│  PDF Text   │ │  RAG Chain   │ │  Document Metadata Store     │
│  Extraction │ │  (LangChain) │ │  (SQLite + FTS5)             │
│  + OCR      │ │              │ │  + Conversations             │
└──────┬──────┘ └──────┬───────┘ └──────────────────────────────┘
       │               │
       ▼               ▼
┌──────────────┐ ┌──────────────────┐ ┌──────────────────────────┐
│  Text        │ │  ChromaDB        │ │  Groq API (Cloud LLM)    │
│  Splitting   │ │  (Vector Store)  │ │  Llama 3.3 70B           │
└──────────────┘ └────────┬─────────┘ └──────────────────────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │  Sentence        │
                 │  Transformers    │
                 │  (Embeddings)    │
                 │  all-MiniLM-L6-v2│
                 └──────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    NOTIFICATIONS (Twilio)                        │
│  WhatsApp: Commit notifications (GitHub Actions)                │
│  WhatsApp: PDF upload notifications (Backend)                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Stack Tecnológico

| Capa              | Tecnología                        | Justificación                                      |
| ----------------- | --------------------------------- | -------------------------------------------------- |
| **Frontend**      | Next.js 16 (App Router)           | SSR, React 19, API routes, drag & drop real         |
| **UI**            | Tailwind CSS 4 + react-markdown   | Estilos utilitarios, rendering de markdown en chat  |
| **Backend API**   | FastAPI (Python)                  | Async, rápido, OpenAPI docs automáticas             |
| **PDF Extraction**| PyPDF + pdfplumber + pytesseract  | Extracción robusta de texto, tablas y OCR para PDFs escaneados |
| **Text Splitting**| LangChain TextSplitters           | Chunking semántico con overlap configurable         |
| **Embeddings**    | Sentence Transformers             | Modelo `all-MiniLM-L6-v2` (384 dims, local, gratis)|
| **Vector Store**  | ChromaDB (embedded)               | Gratuito, local, persistente, sin servidor externo  |
| **LLM**           | Groq API — Llama 3.3 70B         | Gratuito (14,400 req/día), ultra rápido (LPU)      |
| **Orchestration** | LangChain                         | Pipeline RAG completo con retriever + chain          |
| **DB Metadata**   | SQLite + FTS5                     | Local, robusto, full-text search para BM25          |
| **Notifications** | Twilio WhatsApp API               | Notificaciones de commits y uploads vía WhatsApp    |
| **Chat Export**   | jspdf (PDF) + Markdown            | Exportar conversaciones en múltiples formatos       |
| **Rate Limiting** | slowapi                           | Protección contra abuso de API                      |
| **OCR**           | pytesseract + Tesseract           | Extracción de texto de PDFs escaneados              |
| **Testing**       | Vitest + pytest                   | Tests unitarios frontend y backend                  |
| **Dev Scripts**   | concurrently                      | Arranca backend + frontend con un solo comando      |

---

## 3. LLM — Groq API (100% Gratuito, Cloud)

### Por qué Groq
- **14,400 requests/día** gratis sin tarjeta de crédito
- **30 requests/minuto** — suficiente para uso personal/proyecto
- **Llama 3.3 70B** — modelo de 70B parámetros, calidad frontier
- **Hardware LPU** custom — 5-10x más rápido que GPUs estándar
- **API compatible con OpenAI** — fácil integración
- **No consume RAM local** — todo corre en la nube de Groq

### Obtener API Key (gratis)
1. Ir a https://console.groq.com
2. Crear cuenta (sin tarjeta)
3. Generar API key
4. Guardar como `GROQ_API_KEY` en `.env`

### Modelos disponibles en tier free
| Modelo | Velocidad | Uso |
|--------|-----------|-----|
| `llama-3.3-70b-versatile` | Rápida | **Recomendado — mejor calidad** |
| `llama-3.1-8b-instant` | Muy rápida | Queries simples, bajo costo tokens |
| `gemma2-9b-it` | Rápida | Alternativa ligera |
| `mixtral-8x7b-32768` | Rápida | Buen contexto largo |

---

## 4. Embeddings (Local, Gratuito)

| Modelo | Dim | Velocidad | Precision | Uso |
|--------|-----|-----------|-----------|-----|
| `all-MiniLM-L6-v2` | 384 | Muy rápida | Buena | **Recomendado para empezar** |
| `all-mpnet-base-v2` | 768 | Media | Muy alta | Más precisión, más lento |
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | Rápida | Buena | Soporte multilingüe (español) |

---

## 5. Flujo del Pipeline RAG

### 5.1 Ingesta de PDFs
```
PDF Upload (max 50 MB) → Validación magic bytes %PDF + tamaño + extensión
    → Detección de duplicados (MD5 hash)
    → Extracción texto (PyPDF/pdfplumber)
    → Chunking (LangChain, 500 chars, 50 overlap)
    → Embeddings (Sentence Transformers, local)
    → Almacenar en ChromaDB + SQLite FTS5
    → Guardar metadata en SQLite
```

### 5.2 Consulta (Query)
```
User Query → Embedding de la query (local)
    → Búsqueda híbrida: ChromaDB (vectorial) + SQLite FTS5 (BM25)
    → Reciprocal Rank Fusion para combinar resultados
    → Construir prompt con contexto + pregunta
    → Enviar a Groq API (Llama 3.3 70B, cloud)
    → Streaming de respuesta (SSE)
    → Respuesta con fuentes citadas (rendered como markdown)
```

---

## 6. Estructura del Proyecto

```
pageyn/
├── frontend/                  # Next.js App
│   ├── app/
│   │   ├── layout.tsx         # Layout raíz con nav + dark mode
│   │   ├── page.tsx           # Dashboard principal (stats)
│   │   ├── not-found.tsx      # Página 404
│   │   ├── error.tsx          # Error boundary root
│   │   ├── global-error.tsx   # Error boundary layout
│   │   ├── upload/
│   │   │   ├── page.tsx       # Subir PDFs (drag & drop, parallel)
│   │   │   ├── loading.tsx    # Loading state
│   │   │   └── error.tsx      # Error boundary upload
│   │   ├── documents/
│   │   │   ├── page.tsx       # Listar, eliminar, batch delete, thumbnails
│   │   │   ├── loading.tsx    # Loading state
│   │   │   └── error.tsx      # Error boundary documents
│   │   └── chat/
│   │       ├── page.tsx       # Multi-select docs, save/load chat, export
│   │       ├── loading.tsx    # Loading state
│   │       └── error.tsx      # Error boundary chat
│   ├── components/
│   │   ├── BatchActionBar.tsx # Barra de acciones para batch delete
│   │   ├── ChatExportMenu.tsx # Menú exportar chat (Markdown + PDF)
│   │   ├── DocumentCard.tsx   # Card con thumbnail + checkbox selection
│   │   ├── EmptyState.tsx     # Estado vacío genérico
│   │   ├── ErrorFallback.tsx  # Fallback de error boundaries
│   │   ├── LoadingSpinner.tsx # Spinner de carga
│   │   ├── MarkdownMessage.tsx# Rendering markdown
│   │   ├── NavLinks.tsx       # Navegación responsive (hamburger)
│   │   ├── SourceCitation.tsx # Fuentes de respuestas
│   │   ├── StatusCard.tsx     # Cards de éxito/error
│   │   └── ThemeToggle.tsx    # Toggle dark/light mode
│   ├── hooks/
│   │   ├── useChatPersistence.ts # Persistencia chat (server + localStorage)
│   │   └── useTheme.ts       # Hook de tema dark/light
│   ├── hooks/__tests__/       # Tests de hooks
│   │   ├── useChatPersistence.test.ts
│   │   └── useTheme.test.ts
│   ├── __tests__/             # Tests frontend (Vitest)
│   │   ├── ErrorFallback.test.tsx
│   │   ├── SourceCitation.test.tsx
│   │   ├── EmptyState.test.tsx
│   │   ├── StatusCard.test.tsx
│   │   ├── LoadingSpinner.test.tsx
│   │   └── MarkdownMessage.test.tsx
│   ├── vitest.config.ts       # Config Vitest
│   ├── setupTests.ts          # Setup testing-library
│   └── package.json
│
├── backend/                   # FastAPI
│   ├── main.py                # App FastAPI + lifespan
│   ├── config.py              # Configuración (incluye OCR_ENABLED, OCR_LANGUAGE)
│   ├── database.py            # SQLite metadata store + FTS5 + conversations
│   ├── rate_limit.py          # Rate limiting (slowapi)
│   ├── routers/
│   │   ├── documents.py       # CRUD documentos + batch delete + thumbnails
│   │   ├── query.py           # Endpoint de consulta + streaming
│   │   └── conversations.py   # CRUD conversaciones chat
│   ├── services/
│   │   ├── pdf_extractor.py   # Extracción de texto + OCR fallback
│   │   ├── text_splitter.py   # Chunking
│   │   ├── embeddings.py      # Generación de embeddings (async)
│   │   ├── vector_store.py    # Operaciones ChromaDB + BM25 híbrido
│   │   ├── llm.py             # Integración Groq API
│   │   ├── summarizer.py      # Auto-summary de PDFs (Groq)
│   │   ├── notifications.py   # WhatsApp notifications (Twilio)
│   │   └── duplicate_detector.py # Detección de duplicados (MD5)
│   ├── models/
│   │   └── document.py        # Modelos Pydantic (incluye summary)
│   ├── tests/                 # Tests backend (pytest)
│   │   ├── conftest.py        # Fixtures AsyncClient
│   │   ├── test_documents.py  # Tests upload/list/delete/stats
│   │   ├── test_query.py      # Tests query/health/streaming
│   │   ├── test_notifications.py # Tests WhatsApp notifications
│   │   ├── test_duplicate_detector.py
│   │   ├── test_embeddings.py
│   │   ├── test_pdf_extractor.py
│   │   ├── test_text_splitter.py
│   │   └── test_vector_store.py
│   ├── pytest.ini             # Config pytest
│   └── requirements.txt
│
├── data/
│   ├── chroma/                # ChromaDB persistente
│   ├── metadata.db            # SQLite metadata + FTS5
│   └── pdfs/                  # PDFs originales
│
├── .env.local.example         # Template de variables de entorno
├── package.json               # Scripts de ejecución (raíz)
├── stack.md                   # Este archivo
└── README.md
```

---

## 7. Configuración y Dependencias

### Paquete Raíz (package.json)
```json
{
  "name": "pageyn",
  "scripts": {
    "dev": "concurrently \"npm run dev:backend\" \"npm run dev:frontend\"",
    "dev:backend": "cd backend && python3 -m uvicorn backend.main:app --reload --port 8000",
    "dev:frontend": "cd frontend && npm run dev",
    "build": "cd frontend && npm run build",
    "install:all": "cd frontend && npm install && cd ../backend && pip3 install -r requirements.txt"
  },
  "devDependencies": {
    "concurrently": "^9.0.0"
  }
}
```

### Backend (requirements.txt)
```
fastapi==0.115.0
uvicorn==0.32.0
python-multipart==0.0.12
pypdf==5.1.0
pdfplumber==0.11.10
langchain==0.3.14
langchain-text-splitters==0.3.4
sentence-transformers==3.3.1
chromadb==0.5.23
groq==0.13.0
pydantic==2.13.4
aiosqlite==0.22.1
python-dotenv==1.0.1
slowapi==0.1.10
pytest==8.3.4
pytest-asyncio==0.25.0
httpx==0.28.1
pytesseract>=0.3.10
Pillow>=10.0.0
```

### Frontend (package.json)
```json
{
  "name": "frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "eslint",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "@tailwindcss/typography": "^0.5.20",
    "jspdf": "^2.5.2",
    "lucide-react": "^1.24.0",
    "next": "16.2.10",
    "react": "19.2.7",
    "react-dom": "19.2.7",
    "react-markdown": "^10.1.0"
  },
  "devDependencies": {
    "@tailwindcss/postcss": "^4.3.3",
    "@testing-library/jest-dom": "^6.9.1",
    "@testing-library/react": "^16.3.2",
    "@testing-library/user-event": "^14.6.1",
    "@types/node": "^20",
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "@vitejs/plugin-react": "^6.0.3",
    "eslint": "^9",
    "eslint-config-next": "16.2.10",
    "jsdom": "^29.1.1",
    "tailwindcss": "^4.3.3",
    "typescript": "^5",
    "vitest": "^4.1.10"
  }
}
```

---

## 8. Endpoints API

| Método  | Ruta                      | Descripción                                    |
| ------- | ------------------------- | ---------------------------------------------- |
| `POST`  | `/api/documents`          | Subir PDF (max 50 MB), extraer texto, indexar  |
| `GET`   | `/api/documents`          | Listar documentos indexados                    |
| `GET`   | `/api/documents/stats`    | Estadísticas (docs, páginas, chunks, último upload) |
| `GET`   | `/api/documents/{id}/chunks` | Ver chunks indexados de un documento         |
| `GET`   | `/api/documents/{id}/thumbnail` | Thumbnail del PDF (primera página)        |
| `DELETE`| `/api/documents/{id}`     | Eliminar documento y sus embeddings            |
| `DELETE`| `/api/documents/batch`    | Eliminar múltiples documentos (batch delete)   |
| `POST`  | `/api/query`              | Consultar la knowledge base                    |
| `POST`  | `/api/query/stream`       | Consulta con streaming (SSE)                   |
| `GET`   | `/api/health`             | Verificar estado de servicios                  |
| `GET`   | `/api/conversations`      | Listar conversaciones guardadas                |
| `POST`  | `/api/conversations`      | Guardar conversación                           |
| `GET`   | `/api/conversations/{id}` | Obtener conversación con mensajes              |
| `DELETE`| `/api/conversations/{id}` | Eliminar conversación                          |

---

## 9. Variables de Entorno

```env
# backend/.env
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K_RESULTS=5

# OCR (opcional)
OCR_ENABLED=true
OCR_LANGUAGE=spa

# WhatsApp Notifications (Twilio)
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
WHATSAPP_FROM_NUMBER=whatsapp:+14155238886
WHATSAPP_TO_NUMBER=whatsapp:+5491112345678

# frontend/.env.local (opcional)
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

---

## 10. Requisitos del Sistema

| Componente | Mínimo | Recomendado |
|------------|--------|-------------|
| RAM | 2 GB | 4 GB+ |
| Disco | 500 MB libre | 2 GB+ |
| GPU | No requerida | No necesaria |
| OS | macOS / Linux / Windows | Cualquiera |
| Python | 3.10+ | 3.11+ |
| Node.js | 18+ | 20+ |
| Internet | **Requerida** (Groq API) | Estable |

---

## 11. Decisiones Clave

1. **Groq como LLM**: Gratuito, 14,400 req/día, ultra rápido, sin instalar nada local
2. **Embeddings locales**: Sentence Transformers no tiene costo ni límite de API
3. **ChromaDB embebido**: Sin servidor vectorial separado
4. **FastAPI separado de Next.js**: Permite escalar independientemente
5. **SQLite para metadata**: Local, robusto, soporta FTS5 para búsqueda full-text
6. **LangChain como orquestador**: Pipeline RAG completo con integraciones nativas
7. **concurrently en raíz**: Un solo comando `npm run dev` arranca backend + frontend
8. **Error boundaries por ruta**: `error.tsx` en cada segmento + `global-error.tsx` para el layout
9. **Drag-and-drop real**: API nativa de HTML5, validación PDF + tamaño antes de enviar
10. **Markdown en chat**: react-markdown con estilos prose para renderizar respuestas del LLM
11. **Persistencia del chat**: SQLite server-side + localStorage fallback, historial individual por documento
12. **Multi-select documentos**: Checkbox para seleccionar varios PDFs en el chat
13. **Búsqueda híbrida BM25 + vectorial**: Reciprocal Rank Fusion para mejores resultados
14. **Detección de duplicados**: MD5 hash, evita re-indexar PDFs existentes
15. **Thumbnails de PDFs**: Preview visual de la primera página
16. **Export de conversaciones**: Descargar chat como Markdown o PDF (jspdf)
17. **Ver chunks indexados**: Modal para auditar calidad del chunking
18. **Precarga de modelo**: SentenceTransformer se carga en startup, no en primer request
19. **SSE parsing robusto**: Buffer acumulador para evitar JSON truncado
20. **Seguridad**: Magic bytes %PDF, sanitización anti-prompt injection, límite de longitud
21. **OCR para PDFs escaneados**: pytesseract + Tesseract como fallback cuando PyPDF/pdfplumber no extraen texto
22. **Auto-summary**: Generación automática de resúmenes vía Groq API al subir PDFs
23. **WhatsApp notifications**: Notificaciones de commits (GitHub Actions) y uploads (Twilio API)
24. **Batch delete**: Eliminar múltiples documentos de una vez con selección múltiple
25. **Rate limiting activo**: slowapi protege todos los endpoints contra abuso
26. **Chat export PDF**: Generación de PDFs profesionales con jspdf para compartir conversaciones

---

## 12. Instalación y Ejecución

### Instalación Rápida
```bash
cd pageyn
npm install                          # instala concurrently en raíz
npm run install:all                  # instala frontend + backend
```

### Configurar API Key
```bash
# Obtener gratis en https://console.groq.com
echo "GROQ_API_KEY=tu_api_key_aqui" > backend/.env
```

### Iniciar Todo
```bash
cd pageyn
npm run dev                          # arranca backend (8000) + frontend (3000)
```

### Scripts
```bash
npm run dev                          # arranca backend (8000) + frontend (3000)
npm run dev:backend                  # solo FastAPI en :8000
npm run dev:frontend                 # solo Next.js en :3000
npm run build                        # build de producción del frontend
npm run install:all                  # instala frontend + backend
```

### GitHub Actions
- `.github/workflows/whatsapp-notify.yml` — Notifica commits y PRs vía WhatsApp

### Tests
```bash
cd frontend && npm run test          # tests frontend (Vitest)
cd backend && python3 -m pytest backend/tests/ -v  # tests backend (pytest)
```

### URLs
| Servicio | URL |
|----------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

---

## 13. Seguridad

| Medida | Implementación |
|--------|----------------|
| Rate limiting | slowapi (activado en todos los endpoints) |
| Magic bytes validation | Verifica `%PDF` al inicio del archivo |
| Prompt injection | System prompt con disclaimer + ignorar instrucciones del contexto |
| Límite de tokens | Preguntas máximas 2000 caracteres |
| CORS | Solo localhost:3000 |
| File size | 50 MB máximo |
| Duplicados | MD5 hash, evita re-indexación |
| BM25 sanitization | Limpieza de operadores FTS5 (AND, OR, NOT, NEAR, etc.) |

---

## 14. Testing

### Backend (38 tests)
| Suite | Tests |
|-------|-------|
| test_documents.py | 10 |
| test_query.py | 5 |
| test_duplicate_detector.py | 6 |
| test_embeddings.py | 4 |
| test_pdf_extractor.py | 2 |
| test_text_splitter.py | 3 |
| test_vector_store.py | 3 |
| test_notifications.py | 5 |

### Frontend (31 tests)
| Suite | Tests |
|-------|-------|
| useChatPersistence.test.ts | 11 |
| useTheme.test.ts | 7 |
| ErrorFallback.test.tsx | 2 |
| SourceCitation.test.tsx | 2 |
| EmptyState.test.tsx | 2 |
| StatusCard.test.tsx | 2 |
| LoadingSpinner.test.tsx | 2 |
| MarkdownMessage.test.tsx | 3 |
