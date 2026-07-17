import re
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response

from backend.config import PDF_DIR, MAX_FILE_SIZE
from backend.models.document import DocumentResponse, StatsResponse
from backend.services.pdf_extractor import extract_text
from backend.services.text_splitter import split_pages
from backend.services.vector_store import add_documents, delete_document, get_document_count
from backend.services.duplicate_detector import compute_content_hash
from backend.database import load_metadata, save_document, delete_document_metadata, get_document_by_hash, save_chunks, delete_chunks, get_chunks_by_doc

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

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="El archivo esta vacio")

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"El archivo excede el limite de {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )

    if not content[:5] == b"%PDF-":
        raise HTTPException(status_code=400, detail="El archivo no es un PDF válido")

    content_hash = compute_content_hash(content)

    existing = get_document_by_hash(content_hash)
    if existing:
        doc_id = uuid.uuid4().hex[:12]
        safe_name = _sanitize_filename(file.filename)
        pdf_path = PDF_DIR / f"{doc_id}_{safe_name}"
        pdf_path.write_bytes(content)
        return DocumentResponse(
            id=existing["id"],
            filename=file.filename,
            pages=existing["pages"],
            chunks=existing["chunks"],
            uploaded_at=existing["uploaded_at"],
            duplicate_of=existing["id"],
        )

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

        chunk_data = [
            {
                "chunk_id": f"{doc_id}_chunk_{i}",
                "content": chunk.page_content,
                "source": chunk.metadata.get("source", ""),
                "page": chunk.metadata.get("page", 0),
            }
            for i, chunk in enumerate(chunks)
        ]
        save_chunks(doc_id, chunk_data)

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

    delete_chunks(doc_id)
    delete_document_metadata(doc_id)

    return {"deleted_chunks": deleted}


@router.get("/{doc_id}/chunks")
async def get_document_chunks(doc_id: str):
    metadata = load_metadata()
    if doc_id not in metadata:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    chunks = get_chunks_by_doc(doc_id)
    return {
        "doc_id": doc_id,
        "filename": metadata[doc_id]["filename"],
        "chunks": [
            {
                "chunk_id": c["chunk_id"],
                "content": c["content"],
                "source": c["source"],
                "page": c["page"],
            }
            for c in chunks
        ],
    }


@router.get("/{doc_id}/thumbnail")
async def get_document_thumbnail(doc_id: str):
    metadata = load_metadata()
    if doc_id not in metadata:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    pdf_files = list(PDF_DIR.glob(f"{doc_id}_*"))
    if not pdf_files:
        raise HTTPException(status_code=404, detail="Archivo PDF no encontrado")

    try:
        from pypdf import PdfReader
        from pypdf import PageObject
        from io import BytesIO
        from PIL import Image

        reader = PdfReader(str(pdf_files[0]))
        if len(reader.pages) == 0:
            raise HTTPException(status_code=422, detail="PDF sin páginas")

        page = reader.pages[0]
        text = page.extract_text() or ""

        img = Image.new("RGB", (200, 280), "white")
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
            small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 10)
        except Exception:
            font = ImageFont.load_default()
            small_font = font

        draw.rectangle([0, 0, 199, 30], fill="#3B82F6")
        draw.text((10, 8), metadata[doc_id]["filename"][:25], fill="white", font=small_font)

        lines = text[:500].split("\n")
        y = 40
        for line in lines[:12]:
            draw.text((10, y), line[:30], fill="#374151", font=small_font)
            y += 18

        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        return Response(content=buf.getvalue(), media_type="image/png")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Error generando thumbnail")
