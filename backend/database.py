import re
import sqlite3
from backend.config import DATA_DIR

DB_PATH = DATA_DIR / "metadata.db"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def sanitize_fts5_query(query: str) -> str:
    # Eliminar operadores especiales de FTS5 que pueden alterar la búsqueda
    # Mantener solo texto plano para búsqueda segura
    sanitized = re.sub(r'["*+\-^:(){}[\]<>]', ' ', query)
    sanitized = re.sub(r'\b(AND|OR|NOT|NEAR)\b', ' ', sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    if not sanitized:
        sanitized = '""'
    return sanitized


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                pages INTEGER NOT NULL,
                chunks INTEGER NOT NULL,
                uploaded_at TEXT NOT NULL,
                summary TEXT DEFAULT ''
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                doc_ids TEXT NOT NULL,
                title TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
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
            """INSERT OR REPLACE INTO documents (id, filename, content_hash, pages, chunks, uploaded_at, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (doc["id"], doc["filename"], doc["content_hash"], doc["pages"], doc["chunks"], doc["uploaded_at"], doc.get("summary", "")),
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
    safe_query = sanitize_fts5_query(query)
    with get_db() as conn:
        if doc_ids:
            placeholders = ",".join("?" for _ in doc_ids)
            rows = conn.execute(
                f"""SELECT c.doc_id, c.chunk_id, c.content, c.source, c.page,
                    rank FROM chunks_fts f
                    JOIN chunks c ON f.rowid = c.rowid
                    WHERE chunks_fts MATCH ? AND c.doc_id IN ({placeholders})
                    ORDER BY rank LIMIT ?""",
                [safe_query] + doc_ids + [top_k],
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT c.doc_id, c.chunk_id, c.content, c.source, c.page,
                    rank FROM chunks_fts f
                    JOIN chunks c ON f.rowid = c.rowid
                    WHERE chunks_fts MATCH ?
                    ORDER BY rank LIMIT ?""",
                (safe_query, top_k),
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


def create_conversation(conversation_id: str, doc_ids: list[str], title: str | None = None) -> dict:
    import json
    import time
    now = str(time.time())
    with get_db() as conn:
        conn.execute(
            """INSERT INTO conversations (id, doc_ids, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)""",
            (conversation_id, json.dumps(doc_ids), title, now, now),
        )
        conn.commit()
        return {"id": conversation_id, "doc_ids": doc_ids, "title": title, "created_at": now, "updated_at": now}


def get_conversations() -> list[dict]:
    import json
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM conversations ORDER BY updated_at DESC").fetchall()
        result = []
        for row in rows:
            conv = dict(row)
            conv["doc_ids"] = json.loads(conv["doc_ids"])
            result.append(conv)
        return result


def get_conversation(conversation_id: str) -> dict | None:
    import json
    with get_db() as conn:
        row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
        if row:
            conv = dict(row)
            conv["doc_ids"] = json.loads(conv["doc_ids"])
            return conv
        return None


def delete_conversation(conversation_id: str) -> bool:
    with get_db() as conn:
        conn.execute("DELETE FROM chat_messages WHERE conversation_id = ?", (conversation_id,))
        cursor = conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        conn.commit()
        return cursor.rowcount > 0


def add_chat_message(conversation_id: str, role: str, content: str, sources: list[dict] | None = None) -> dict:
    import json
    import time
    now = str(time.time())
    sources_json = json.dumps(sources) if sources else None
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO chat_messages (conversation_id, role, content, sources, created_at)
            VALUES (?, ?, ?, ?, ?)""",
            (conversation_id, role, content, sources_json, now),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "conversation_id": conversation_id, "role": role, "content": content, "sources": sources, "created_at": now}


def get_chat_messages(conversation_id: str) -> list[dict]:
    import json
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM chat_messages WHERE conversation_id = ? ORDER BY created_at",
            (conversation_id,),
        ).fetchall()
        result = []
        for row in rows:
            msg = dict(row)
            msg["sources"] = json.loads(msg["sources"]) if msg["sources"] else None
            result.append(msg)
        return result


init_db()
