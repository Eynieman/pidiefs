from backend.services.text_splitter import split_pages


def test_split_pages_returns_documents():
    pages = [{"page_num": 1, "content": "Hello world. " * 50}]
    result = split_pages(pages, "test.pdf")
    assert len(result) > 0


def test_split_pages_metadata():
    pages = [{"page_num": 1, "content": "Hello world. " * 50}]
    result = split_pages(pages, "test.pdf")
    for doc in result:
        assert "source" in doc.metadata
        assert "page" in doc.metadata
        assert doc.metadata["source"] == "test.pdf"
        assert doc.metadata["page"] == 1


def test_split_pages_multiple_pages():
    pages = [
        {"page_num": 1, "content": "Page one content. " * 50},
        {"page_num": 2, "content": "Page two content. " * 50},
    ]
    result = split_pages(pages, "test.pdf")
    assert len(result) > 0
    pages_in_result = {doc.metadata["page"] for doc in result}
    assert 1 in pages_in_result
    assert 2 in pages_in_result
