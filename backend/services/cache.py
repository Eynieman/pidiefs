import hashlib
import json
from cachetools import TTLCache

llm_answer_cache = TTLCache(maxsize=500, ttl=3600)
query_embedding_cache = TTLCache(maxsize=1000, ttl=1800)
followup_cache = TTLCache(maxsize=500, ttl=3600)
pdf_summary_cache = TTLCache(maxsize=200, ttl=86400)


def _hash(*args: str) -> str:
    raw = json.dumps(args, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def make_llm_key(question: str, docs: list[dict], query_type: str) -> str:
    docs_snapshot = json.dumps(
        sorted(
            [
                {"content": d.get("content", ""), "metadata": d.get("metadata", {})}
                for d in docs
            ],
            key=lambda x: json.dumps(x, sort_keys=True),
        ),
        sort_keys=True,
    )
    return _hash(question, docs_snapshot, query_type)


def make_embedding_key(query: str) -> str:
    return _hash(query)


def make_followup_key(question: str, answer: str) -> str:
    return _hash(question, answer)


def make_summary_key(filename: str, content: str) -> str:
    return _hash(filename, content)
