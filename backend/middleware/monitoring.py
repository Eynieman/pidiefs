import os
import time
import logging
import shutil
from collections import defaultdict
from threading import Lock

from fastapi import Request, APIRouter
from slowapi import Limiter

from backend.config import DATA_DIR, APP_START_TIME
from backend.database import get_db
from backend.services.vector_store import get_document_count

logger = logging.getLogger(__name__)

# ─── In-memory counters ──────────────────────────────────────────────────

class MetricsCollector:
    def __init__(self):
        self._lock = Lock()
        self.total_requests = 0
        self.requests_by_method: dict[str, int] = defaultdict(int)
        self.requests_by_status: dict[str, int] = defaultdict(int)
        self.requests_by_endpoint: dict[str, int] = defaultdict(int)
        self.errors_4xx: int = 0
        self.errors_5xx: int = 0
        self.path_traversal_attempts: int = 0
        self._minute_bucket: list[float] = []

    def record(self, method: str, path: str, status_code: int):
        with self._lock:
            self.total_requests += 1
            self.requests_by_method[method] += 1
            category = f"{status_code // 100}xx"
            self.requests_by_status[category] += 1
            self.requests_by_endpoint[path] += 1
            if 400 <= status_code < 500:
                self.errors_4xx += 1
            elif status_code >= 500:
                self.errors_5xx += 1
            self._minute_bucket.append(time.time())

    def record_path_traversal(self):
        with self._lock:
            self.path_traversal_attempts += 1

    def get_metrics(self) -> dict:
        with self._lock:
            now = time.time()
            # Requests in last minute
            cutoff = now - 60
            recent = sum(1 for t in self._minute_bucket if t > cutoff)
            # Clean old entries
            self._minute_bucket = [t for t in self._minute_bucket if t > cutoff]

            disk_usage = shutil.disk_usage(DATA_DIR)
            with get_db() as conn:
                doc_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

            return {
                "uptime_seconds": round(now - APP_START_TIME, 2),
                "total_requests": self.total_requests,
                "requests_by_method": dict(self.requests_by_method),
                "requests_by_status": dict(self.requests_by_status),
                "requests_by_endpoint": dict(self.requests_by_endpoint),
                "errors_4xx": self.errors_4xx,
                "errors_5xx": self.errors_5xx,
                "requests_last_minute": recent,
                "path_traversal_attempts": self.path_traversal_attempts,
                "documents_indexed": doc_count,
                "disk_free_mb": round(disk_usage.free / (1024 * 1024), 1),
                "disk_total_mb": round(disk_usage.total / (1024 * 1024), 1),
            }


metrics = MetricsCollector()

# ─── Admin router ─────────────────────────────────────────────────────────

admin_router = APIRouter(prefix="/api/admin", tags=["admin"])


@admin_router.get("/metrics")
async def get_metrics():
    return metrics.get_metrics()


@admin_router.get("/health")
async def admin_health():
    import shutil
    import psutil

    disk_usage = shutil.disk_usage(DATA_DIR)
    memory = psutil.virtual_memory()
    now = time.time()

    return {
        "status": "ok",
        "uptime_seconds": round(now - APP_START_TIME, 2),
        "version": "1.0.0",
        "documents_indexed": get_document_count(),
        "disk": {
            "free_mb": round(disk_usage.free / (1024 * 1024), 1),
            "total_mb": round(disk_usage.total / (1024 * 1024), 1),
            "used_percent": round(
                (disk_usage.total - disk_usage.free) / disk_usage.total * 100, 1
            ),
        },
        "memory": {
            "available_mb": round(memory.available / (1024 * 1024), 1),
            "total_mb": round(memory.total / (1024 * 1024), 1),
            "used_percent": round(memory.percent, 1),
        },
    }
