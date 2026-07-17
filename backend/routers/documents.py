import re
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

from backend.config import PDF_DIR, MAX_FILE_SIZE
from backend.models.document import DocumentResponse, StatsResponse
from backend.services.pdf_extractor import extract_text
from backend.services.text_splitter import split_pages
from backend.services.vector_store import add_documents, delete_document, get_document_count
from backend.services.duplicate_detector import compute_content_hash
from backend.database import load_metadata, save_document, delete_document_metadata, get_document_by_hash

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_FILENAME_LENGTH = 255


def _sanitize_filename(filename: str) -> str:
    safe = re.sub(r"[^\w\-.]", "_", filename)
    return safe[:MAX_FILENAME_LENGTH]


@router.post("", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")

    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"El archivo excede el limite de {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="El archivo esta vacio")

    content_hash = compute_content_hash(content)

    existing = get_document_by_hash(content_hash)
    duplicate_of = existing["id"] if existing else None

    doc_id = uuid.uuid4().hex[:12]
    safe_name = _sanitize_filename(file.filename)
    pdf_path = PDF_DIR / f"{doc_id}_{safe_name}"
    pdf_path.write_bytes(content)

    try:
        extracted = extract_text(pdf_path)
        if not extracted["pages"]:
            raise HTTPException(
                status_code=422,
                detail="No se pudo extraer texto del PDF",
            )

        chunks = split_pages(extracted["pages"], file.filename)
        num_chunks = await add_documents(chunks, doc_id)

        uploaded_at = str(Path(pdf_path).stat().st_mtime)
        doc = {
            "id": doc_id,
            "filename": file.filename,
            "content_hash": content_hash,
            "pages": extracted["total_pages"],
            "chunks": num_chunks,
            "uploaded_at": uploaded_at,
        }
        save_document(doc)

        return DocumentResponse(
            id=doc_id,
            filename=file.filename,
            pages=extracted["total_pages"],
            chunks=num_chunks,
            uploaded_at=uploaded_at,
            duplicate_of=duplicate_of,
        )

    except HTTPException:
        raise
    except Exception as e:
        pdf_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Error procesando PDF: {str(e)}")


@router.get("", response_model=list[DocumentResponse])
async def list_documents():
    metadata = load_metadata()
    return [DocumentResponse(**doc) for doc in metadata.values()]


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    metadata = load_metadata()
    if not metadata:
        return StatsResponse(
            total_documents=0,
            total_pages=0,
            total_chunks=0,
            last_upload=None,
        )

    total_pages = sum(doc.get("pages", 0) for doc in metadata.values())
    total_chunks = sum(doc.get("chunks", 0) for doc in metadata.values())

    last_upload = None
    max_ts = 0
    for doc in metadata.values():
        ts = float(doc.get("uploaded_at", "0"))
        if ts > max_ts:
            max_ts = ts
            last_upload = doc.get("uploaded_at")

    return StatsResponse(
        total_documents=len(metadata),
        total_pages=total_pages,
        total_chunks=total_chunks,
        last_upload=last_upload,
    )


@router.delete("/{doc_id}")
async def remove_document(doc_id: str):
    metadata = load_metadata()
    if doc_id not in metadata:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    deleted = delete_document(doc_id)

    pdf_files = list(PDF_DIR.glob(f"{doc_id}_*"))
    for f in pdf_files:
        f.unlink(missing_ok=True)

    delete_document_metadata(doc_id)

    return {"deleted_chunks": deleted}
