from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from backend.config import CHUNK_SIZE, CHUNK_OVERLAP


def split_pages(pages: list[dict], filename: str) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    documents = []
    for page in pages:
        doc = Document(
            page_content=page["content"],
            metadata={"source": filename, "page": page["page_num"]},
        )
        documents.append(doc)

    chunks = splitter.split_documents(documents)
    return chunks
