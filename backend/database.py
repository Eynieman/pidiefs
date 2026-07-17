import sqlite3
from backend.config import DATA_DIR

DB_PATH = DATA_DIR / "metadata.db"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            pages INTEGER NOT NULL,
            chunks INTEGER NOT NULL,
            uploaded_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def load_metadata() -> dict:
    conn = get_db()
    rows = conn.execute("SELECT * FROM documents").fetchall()
    conn.close()
    return {row["id"]: dict(row) for row in rows}


def save_document(doc: dict):
    conn = get_db()
    conn.execute(
        """INSERT OR REPLACE INTO documents (id, filename, content_hash, pages, chunks, uploaded_at)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (doc["id"], doc["filename"], doc["content_hash"], doc["pages"], doc["chunks"], doc["uploaded_at"]),
    )
    conn.commit()
    conn.close()


def delete_document_metadata(doc_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def get_document_by_hash(content_hash: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM documents WHERE content_hash = ?", (content_hash,)).fetchone()
    conn.close()
    return dict(row) if row else None


init_db()
