# Stack — PDF Knowledge Base (RAG)

Arquitectura de una aplicación web para consultar PDFs mediante un pipeline de Retrieval-Augmented Generation (RAG).

---

## 1. Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js)                       │
│  ┌───────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Upload UI │  │ Chat / Query │  │ Document List / Status   │  │
│  └─────┬─────┘  └──────┬───────┘  └────────────┬─────────────┘  │
└────────┼───────────────┼───────────────────────┼────────────────┘
         │               │                       │
         ▼               ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API REST (FastAPI)                           │
│  POST /upload    POST /query    GET /documents    DELETE /doc    │
└────┬───────────────┬───────────────────────────┬────────────────┘
     │               │                           │
     ▼               ▼                           ▼
┌─────────────┐ ┌──────────────┐ ┌──────────────────────────────┐
│  PDF Text   │ │  RAG Chain   │ │  Document Metadata Store     │
│  Extraction │ │  (LangChain) │ │  (JSON)                      │
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
```

---

## 2. Stack Tecnológico

| Capa              | Tecnología                   | Justificación                                      |
| ----------------- | ---------------------------- | -------------------------------------------------- |
| **Frontend**      | Next.js 14+ (App Router)     | SSR, React, API routes, upload UI con drag & drop   |
| **Backend API**   | FastAPI (Python)             | Async, rápido, OpenAPI docs automáticas             |
| **PDF Extraction**| PyPDF + pdfplumber           | Extracción robusta de texto y tablas de PDFs        |
| **Text Splitting**| LangChain TextSplitters      | Chunking semántico con overlap configurable         |
| **Embeddings**    | Sentence Transformers        | Modelo `all-MiniLM-L6-v2` (384 dims, local, gratis)|
| **Vector Store**  | ChromaDB (embedded)          | Gratuito, local, persistente, sin servidor externo  |
| **LLM**           | Groq API — Llama 3.3 70B    | Gratuito (14,400 req/día), ultra rápido (LPU)      |
| **Orchestration** | LangChain                    | Pipeline RAG completo con retriever + chain          |
| **DB Metadata**   | JSON file                   | Ligero, sin setup, almacena info de documentos      |
| **Dev Scripts**   | concurrently                 | Arranca backend + frontend con un solo comando      |

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
PDF Upload → Extracción texto (PyPDF/pdfplumber)
    → Chunking (LangChain, 500 chars, 50 overlap)
    → Embeddings (Sentence Transformers, local)
    → Almacenar en ChromaDB
    → Guardar metadata en JSON
```

### 5.2 Consulta (Query)
```
User Query → Embedding de la query (local)
    → Buscar top-K chunks similares en ChromaDB
    → Construir prompt con contexto + pregunta
    → Enviar a Groq API (Llama 3.3 70B, cloud)
    → Respuesta con fuentes citadas
```

---

## 6. Estructura del Proyecto

```
pageyn/
├── frontend/                  # Next.js App
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx           # Dashboard principal
│   │   ├── upload/page.tsx    # Subir PDFs
│   │   ├── documents/page.tsx # Listar y eliminar PDFs
│   │   └── chat/page.tsx      # Consultar knowledge base
│   ├── components/
│   │   ├── FileUpload.tsx
│   │   ├── ChatInterface.tsx
│   │   ├── DocumentList.tsx
│   │   └── SourceCard.tsx
│   └── package.json
│
├── backend/                   # FastAPI
│   ├── main.py                # App FastAPI
│   ├── routers/
│   │   ├── documents.py       # CRUD documentos
│   │   └── query.py           # Endpoint de consulta
│   ├── services/
│   │   ├── pdf_extractor.py   # Extracción de texto
│   │   ├── text_splitter.py   # Chunking
│   │   ├── embeddings.py      # Generación de embeddings
│   │   ├── vector_store.py    # Operaciones ChromaDB
│   │   └── llm.py             # Integración Groq API
│   ├── models/
│   │   └── document.py        # Modelos Pydantic
│   ├── config.py              # Configuración
│   └── requirements.txt
│
├── data/
│   ├── chroma/                # ChromaDB persistente
│   └── pdfs/                  # PDFs originales
│
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
pdfplumber==0.11.4
langchain==0.3.14
langchain-text-splitters==0.3.4
sentence-transformers==3.3.1
chromadb==0.5.23
groq==0.13.0
pydantic==2.10.4
aiosqlite==0.20.0
python-dotenv==1.0.1
```

### Frontend (package.json)
```json
{
  "name": "pageyn-frontend",
  "dependencies": {
    "next": "^14.2.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "lucide-react": "^0.460.0"
  },
  "devDependencies": {
    "tailwindcss": "^3.4.0",
    "typescript": "^5.0.0"
  }
}
```

---

## 8. Endpoints API

| Método  | Ruta              | Descripción                           |
| ------- | ----------------- | ------------------------------------- |
| `POST`  | `/api/documents`  | Subir PDF, extraer texto, indexar     |
| `GET`   | `/api/documents`  | Listar documentos indexados           |
| `DELETE`| `/api/documents/{id}` | Eliminar documento y sus embeddings |
| `POST`  | `/api/query`      | Consultar la knowledge base           |
| `GET`   | `/api/health`     | Verificar estado de servicios         |

---

## 9. Variables de Entorno

```env
# backend/.env
GROQ_API_KEY=gsk_...
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHROMA_PERSIST_DIR=./data/chroma
PDF_STORAGE_DIR=./data/pdfs
CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K_RESULTS=5
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
5. **JSON para metadata**: Ligero, sin configuración, archivo único
6. **LangChain como orquestador**: Pipeline RAG completo con integraciones nativas
7. **concurrently en raíz**: Un solo comando `npm run dev` arranca backend + frontend

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

### Comandos Individuales
```bash
npm run dev:backend                  # solo FastAPI en :8000
npm run dev:frontend                 # solo Next.js en :3000
npm run build                        # build de producción del frontend
```

### URLs
| Servicio | URL |
|----------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
