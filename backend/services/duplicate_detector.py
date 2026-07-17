import hashlib
from pathlib import Path


def compute_content_hash(file_bytes: bytes) -> str:
    return hashlib.md5(file_bytes).hexdigest()


def find_duplicate(content_hash: str, metadata: dict) -> str | None:
    for doc_id, doc in metadata.items():
        if doc.get("content_hash") == content_hash:
            return doc_id
    return None
