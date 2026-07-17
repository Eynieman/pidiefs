import sqlite3
from backend.config import DATA_DIR

DB_PATH = DATA_DIR / "metadata.db"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
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
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                doc_id,
                chunk_id,
                content,
                source,
                page,
                content='chunks',
                content_rowid='rowid'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                content TEXT NOT NULL,
                source TEXT NOT NULL,
                page INTEGER NOT NULL
            )
        """)
        conn.commit()


def load_metadata() -> dict:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM documents").fetchall()
        return {row["id"]: dict(row) for row in rows}


def save_document(doc: dict):
    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO documents (id, filename, content_hash, pages, chunks, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (doc["id"], doc["filename"], doc["content_hash"], doc["pages"], doc["chunks"], doc["uploaded_at"]),
        )
        conn.commit()


def save_chunks(doc_id: str, chunks: list[dict]):
    with get_db() as conn:
        for chunk in chunks:
            conn.execute(
                """INSERT INTO chunks (doc_id, chunk_id, content, source, page)
                VALUES (?, ?, ?, ?, ?)""",
                (doc_id, chunk["chunk_id"], chunk["content"], chunk["source"], chunk["page"]),
            )
        conn.commit()


def delete_chunks(doc_id: str):
    with get_db() as conn:
        conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
        conn.commit()


def bm25_search(query: str, top_k: int = 10, doc_ids: list[str] | None = None) -> list[dict]:
    with get_db() as conn:
        if doc_ids:
            placeholders = ",".join("?" for _ in doc_ids)
            rows = conn.execute(
                f"""SELECT c.doc_id, c.chunk_id, c.content, c.source, c.page,
                    rank FROM chunks_fts f
                    JOIN chunks c ON f.rowid = c.rowid
                    WHERE chunks_fts MATCH ? AND c.doc_id IN ({placeholders})
                    ORDER BY rank LIMIT ?""",
                [query] + doc_ids + [top_k],
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT c.doc_id, c.chunk_id, c.content, c.source, c.page,
                    rank FROM chunks_fts f
                    JOIN chunks c ON f.rowid = c.rowid
                    WHERE chunks_fts MATCH ?
                    ORDER BY rank LIMIT ?""",
                (query, top_k),
            ).fetchall()

        return [
            {
                "content": row["content"],
                "metadata": {"source": row["source"], "page": row["page"], "doc_id": row["doc_id"]},
                "score": abs(row["rank"]),
            }
            for row in rows
        ]


def delete_document_metadata(doc_id: str) -> bool:
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
        return cursor.rowcount > 0


def get_document_by_hash(content_hash: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM documents WHERE content_hash = ?", (content_hash,)).fetchone()
        return dict(row) if row else None


def get_chunks_by_doc(doc_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM chunks WHERE doc_id = ? ORDER BY page, rowid",
            (doc_id,),
        ).fetchall()
        return [dict(row) for row in rows]


init_db()
