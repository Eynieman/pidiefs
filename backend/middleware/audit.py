import os
import logging
import uuid
import time
from logging.handlers import TimedRotatingFileHandler

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.config import DATA_DIR
from backend.middleware.monitoring import metrics

LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "api.log"

_audit_logger: logging.Logger | None = None


def _get_audit_logger() -> logging.Logger:
    global _audit_logger
    if _audit_logger is not None:
        return _audit_logger

    logger = logging.getLogger("audit")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    try:
        from pythonjsonlogger import jsonlogger

        formatter = jsonlogger.JsonFormatter(
            fmt="%(timestamp)s %(request_id)s %(method)s %(path)s %(status_code)s %(duration_ms)s %(client_ip)s %(user_agent)s",
            timestamp=True,
        )
    except ImportError:
        class ManualJsonFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                import json

                log_data = {
                    "timestamp": self.formatTime(record),
                    "request_id": getattr(record, "request_id", ""),
                    "method": getattr(record, "method", ""),
                    "path": getattr(record, "path", ""),
                    "status_code": getattr(record, "status_code", 0),
                    "duration_ms": getattr(record, "duration_ms", 0),
                    "client_ip": getattr(record, "client_ip", ""),
                    "user_agent": getattr(record, "user_agent", ""),
                    "level": record.levelname,
                    "message": record.getMessage(),
                }
                return json.dumps(log_data, ensure_ascii=False)

        formatter = ManualJsonFormatter()

    file_handler = TimedRotatingFileHandler(
        str(LOG_FILE), when="midnight", interval=1, backupCount=30, encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    _audit_logger = logger
    return _audit_logger


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = uuid.uuid4().hex
        request.state.request_id = request_id
        start_time = time.perf_counter()

        # Detect path traversal attempts before processing
        path = request.url.path
        if ".." in path or "%2e%2e" in path.lower():
            metrics.record_path_traversal()
            log = _get_audit_logger()
            log.warning(
                "Posible path traversal detectado",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": path,
                    "client_ip": request.client.host if request.client else "unknown",
                    "alert": "path_traversal",
                },
            )

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        response.headers["X-Request-ID"] = request_id

        # Record metrics
        metrics.record(request.method, path, response.status_code)

        # Detect suspicious patterns
        status_code = response.status_code
        log = _get_audit_logger()
        if status_code in (403, 429) and duration_ms < 100:
            recent_4xx = metrics.errors_4xx
            if recent_4xx > 0 and recent_4xx % 10 == 0:
                log.warning(
                    f"Alta tasa de errores {status_code} detectada ({recent_4xx} total)",
                    extra={
                        "request_id": request_id,
                        "method": request.method,
                        "path": path,
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                        "client_ip": request.client.host if request.client else "unknown",
                        "alert": "high_error_rate",
                    },
                )

        log.info(
            "audit",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", ""),
            },
        )

        return response
