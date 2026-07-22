import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

import time
APP_START_TIME = time.time()
PDF_DIR = DATA_DIR / "pdfs"
CHROMA_DIR = DATA_DIR / "chroma"

PDF_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "5"))
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
OCR_ENABLED = os.getenv("OCR_ENABLED", "true").lower() == "true"
OCR_LANGUAGE = os.getenv("OCR_LANGUAGE", "eng")

CLUSTER_MIN_CHUNKS = int(os.getenv("CLUSTER_MIN_CHUNKS", "5"))
CLUSTER_MIN_CLUSTERS = int(os.getenv("CLUSTER_MIN_CLUSTERS", "2"))
CLUSTER_MAX_CLUSTERS = int(os.getenv("CLUSTER_MAX_CLUSTERS", "15"))
CLUSTER_UMAP_COMPONENTS = int(os.getenv("CLUSTER_UMAP_COMPONENTS", "10"))
HYBRID_TOP_K = int(os.getenv("HYBRID_TOP_K", "8"))
GLOBAL_TOP_K = int(os.getenv("GLOBAL_TOP_K", "8"))
SUMMARY_MAX_SECTIONS = int(os.getenv("SUMMARY_MAX_SECTIONS", "15"))
SUMMARY_GLOBAL_SAMPLE_CHARS = int(os.getenv("SUMMARY_GLOBAL_SAMPLE_CHARS", "8000"))
