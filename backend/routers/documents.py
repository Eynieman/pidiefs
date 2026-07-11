import uuid
import json
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

from backend.config import PDF_DIR
from backend.models.document import DocumentResponse
from backend.services.pdf_extractor import extract_text
from backend.services.text_splitter import split_pages
from backend.services.vector_store import add_documents, delete_document, get_document_count

router = APIRouter(prefix="/api/documents", tags=["documents"])

METADATA_FILE = PDF_DIR / "metadata.json"


def _load_metadata() -> dict:
    if METADATA_FILE.exists():
        return json.loads(METADATA_FILE.read_text())
    return {}


def _save_metadata(data: dict):
    METADATA_FILE.write_text(json.dumps(data, indent=2))


@router.post("", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")

    doc_id = uuid.uuid4().hex[:12]
    pdf_path = PDF_DIR / f"{doc_id}_{file.filename}"

    content = await file.read()
    pdf_path.write_bytes(content)

    try:
        extracted = extract_text(pdf_path)
        if not extracted["pages"]:
            raise HTTPException(
                status_code=422,
                detail="No se pudo extraer texto del PDF",
            )

        chunks = split_pages(extracted["pages"], file.filename)
        num_chunks = add_documents(chunks, doc_id)

        metadata = _load_metadata()
        metadata[doc_id] = {
            "id": doc_id,
            "filename": file.filename,
            "pages": extracted["total_pages"],
            "chunks": num_chunks,
            "uploaded_at": str(Path(pdf_path).stat().st_mtime),
        }
        _save_metadata(metadata)

        return DocumentResponse(
            id=doc_id,
            filename=file.filename,
            pages=extracted["total_pages"],
            chunks=num_chunks,
            uploaded_at=metadata[doc_id]["uploaded_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        pdf_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Error procesando PDF: {str(e)}")


@router.get("", response_model=list[DocumentResponse])
async def list_documents():
    metadata = _load_metadata()
    return [
        DocumentResponse(**doc)
        for doc in metadata.values()
    ]


@router.delete("/{doc_id}")
async def remove_document(doc_id: str):
    metadata = _load_metadata()
    if doc_id not in metadata:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    deleted = delete_document(doc_id)

    pdf_files = list(PDF_DIR.glob(f"{doc_id}_*"))
    for f in pdf_files:
        f.unlink(missing_ok=True)

    del metadata[doc_id]
    _save_metadata(metadata)

    return {"deleted_chunks": deleted}
