from backend.services.duplicate_detector import compute_content_hash, find_duplicate


def test_compute_content_hash_deterministic():
    data = b"hello world"
    assert compute_content_hash(data) == compute_content_hash(data)


def test_compute_content_hash_different():
    assert compute_content_hash(b"hello") != compute_content_hash(b"world")


def test_compute_content_hash_returns_hex_string():
    result = compute_content_hash(b"test")
    assert isinstance(result, str)
    assert len(result) == 32


def test_find_duplicate_found():
    metadata = {
        "doc1": {"content_hash": "abc123"},
        "doc2": {"content_hash": "def456"},
    }
    assert find_duplicate("abc123", metadata) == "doc1"
    assert find_duplicate("def456", metadata) == "doc2"


def test_find_duplicate_not_found():
    metadata = {"doc1": {"content_hash": "abc123"}}
    assert find_duplicate("xyz", metadata) is None


def test_find_duplicate_empty_metadata():
    assert find_duplicate("abc", {}) is None
