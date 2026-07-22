import asyncio
import re
import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Request, Depends
from fastapi.responses import Response

from backend.config import PDF_DIR, MAX_FILE_SIZE
from backend.models.document import DocumentResponse, StatsResponse
from backend.services.pdf_extractor import extract_text
from backend.services.text_splitter import split_pages
from backend.services.vector_store import add_documents, add_summary_documents, delete_document, get_document_count
from backend.services.duplicate_detector import compute_content_hash
from backend.database import load_metadata, save_document, delete_document_metadata, get_document_by_hash, save_chunks, delete_chunks, get_chunks_by_doc, get_db
from backend.services.notifications import notify_pdf_upload
from backend.services.summarizer import generate_pdf_summary, summarize_cluster, generate_global_summary_enhanced
from backend.models.document import BatchDeleteRequest
from backend.rate_limit import limiter
from backend.services.embeddings import embed_texts
from backend.services.clusterer import cluster_chunks
import numpy as np

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_FILENAME_LENGTH = 255
MAX_DOCUMENTS_PER_INSTANCE = 1000

DOC_ID_PATTERN = re.compile(r"^[a-f0-9]{12}$")


def _validate_doc_id(doc_id: str) -> None:
    if not DOC_ID_PATTERN.match(doc_id):
        raise HTTPException(status_code=400, detail="ID de documento invalido")


def _sanitize_filename(filename: str) -> str:
    safe = re.sub(r"[^\w\-.]", "_", filename)
    safe = safe.lstrip("._-")
    return safe[:MAX_FILENAME_LENGTH] or "_"


def _generate_summary(doc_id: str, filename: str, content: str):
    summary = generate_pdf_summary(filename, content)
    if summary:
        with get_db() as conn:
            conn.execute("UPDATE documents SET summary = ? WHERE id = ?", (summary, doc_id))
            conn.commit()


async def _generate_and_index_cluster_summaries(
    doc_id: str,
    filename: str,
    pages: list[dict],
    chunk_texts: list[str],
    embeddings_list: list[list[float]],
):
    embeddings_np = np.array(embeddings_list) if embeddings_list else np.array([])

    if len(chunk_texts) >= 5 and len(embeddings_np) > 0:
        clusters = cluster_chunks(chunk_texts, embeddings_np)

        section_summaries = []
        for cluster in clusters:
            cluster_texts = cluster["texts"]
            if not cluster_texts:
                continue
            result = summarize_cluster(cluster_texts, cluster["cluster_id"])
            result["source"] = filename
            section_summaries.append(result)

        if section_summaries:
            await add_summary_documents(section_summaries, doc_id, abstraction_level=1)
            logger.info(
                "Indexed %d section summaries (level 1) for doc %s",
                len(section_summaries),
                doc_id,
            )

            global_summary = generate_global_summary_enhanced(filename, pages, section_summaries)
            if global_summary:
                await add_summary_documents(
                    [{"content": global_summary, "title": "Resumen Global", "source": filename}],
                    doc_id,
                    abstraction_level=2,
                )
                with get_db() as conn:
                    conn.execute("UPDATE documents SET summary = ? WHERE id = ?", (global_summary, doc_id))
                    conn.commit()
                logger.info("Indexed global summary (level 2) for doc %s", doc_id)
                return
    else:
        logger.info("Fewer than 5 chunks for doc %s, skipping clustering", doc_id)

    global_summary = generate_global_summary_enhanced(filename, pages, section_summaries=None)
    if global_summary:
        await add_summary_documents(
            [{"content": global_summary, "title": "Resumen Global", "source": filename}],
            doc_id,
            abstraction_level=2,
        )
        with get_db() as conn:
            conn.execute("UPDATE documents SET summary = ? WHERE id = ?", (global_summary, doc_id))
            conn.commit()
        logger.info("Indexed global summary (level 2) for doc %s (no clustering)", doc_id)


import logging
logger = logging.getLogger(__name__)


@router.post("", response_model=DocumentResponse)
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
):
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")

    content_type = file.content_type or ""
    if content_type and content_type not in ("application/pdf", "application/octet-stream", ""):
        raise HTTPException(status_code=400, detail="Tipo MIME del archivo no valido")

    content = await file.read()

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="El archivo esta vacio")

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"El archivo excede el limite de {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )

    if not content[:5] == b"%PDF-":
        raise HTTPException(status_code=400, detail="El archivo no es un PDF valido")

    metadata = load_metadata()
    if len(metadata) >= MAX_DOCUMENTS_PER_INSTANCE:
        raise HTTPException(
            status_code=413,
            detail=f"Limite de {MAX_DOCUMENTS_PER_INSTANCE} documentos alcanzado",
        )

    content_hash = compute_content_hash(content)

    existing = get_document_by_hash(content_hash)
    if existing:
        return DocumentResponse(
            id=existing["id"],
            filename=file.filename,
            pages=existing["pages"],
            chunks=existing["chunks"],
            uploaded_at=existing["uploaded_at"],
            duplicate_of=existing["id"],
        )

    MIN_FREE_SPACE = 500 * 1024 * 1024
    disk_usage = shutil.disk_usage(PDF_DIR)
    if disk_usage.free < MIN_FREE_SPACE:
        raise HTTPException(
            status_code=413,
            detail="Espacio en disco insuficiente para almacenar el archivo",
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
        num_chunks = await add_documents(chunks, doc_id, abstraction_level=0)

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

        if background_tasks:
            background_tasks.add_task(
                notify_pdf_upload,
                filename=file.filename,
                pages=extracted["total_pages"],
                chunks=num_chunks,
                doc_id=doc_id,
            )
            page_texts = " ".join(p["content"] for p in extracted["pages"])
            background_tasks.add_task(
                _generate_summary,
                doc_id=doc_id,
                filename=file.filename,
                content=page_texts,
            )

            chunk_texts = [chunk.page_content for chunk in chunks]
            chunk_embeddings_list = None
            try:
                chunk_embeddings_list = await embed_texts(chunk_texts)
            except Exception as e:
                logger.warning("Failed to precompute embeddings for clustering: %s", e)

            asyncio.create_task(
                _generate_and_index_cluster_summaries(
                    doc_id=doc_id,
                    filename=file.filename,
                    pages=extracted["pages"],
                    chunk_texts=chunk_texts,
                    embeddings_list=chunk_embeddings_list,
                )
            )

        return DocumentResponse(
            id=doc_id,
            filename=file.filename,
            pages=extracted["total_pages"],
            chunks=num_chunks,
            uploaded_at=uploaded_at,
            summary=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        pdf_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Error procesando PDF: {str(e)}")


@router.get("", response_model=list[DocumentResponse])
@limiter.limit("30/minute")
async def list_documents(request: Request):
    metadata = load_metadata()
    return [DocumentResponse(**doc) for doc in metadata.values()]


@router.get("/stats", response_model=StatsResponse)
@limiter.limit("30/minute")
async def get_stats(request: Request):
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


@router.delete("/batch")
@limiter.limit("5/minute")
async def batch_delete_documents(request: Request, body: BatchDeleteRequest):
    metadata = load_metadata()
    deleted_count = 0
    total_chunks_deleted = 0

    for doc_id in body.doc_ids:
        _validate_doc_id(doc_id)
        if doc_id not in metadata:
            continue

        deleted = delete_document(doc_id)
        total_chunks_deleted += deleted

        pdf_files = list(PDF_DIR.glob(f"{doc_id}_*"))
        for f in pdf_files:
            f.unlink(missing_ok=True)

        delete_chunks(doc_id)
        delete_document_metadata(doc_id)
        deleted_count += 1

    return {"deleted_documents": deleted_count, "deleted_chunks": total_chunks_deleted}


@router.delete("/{doc_id}")
@limiter.limit("10/minute")
async def remove_document(request: Request, doc_id: str):
    _validate_doc_id(doc_id)
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
@limiter.limit("20/minute")
async def get_document_chunks(request: Request, doc_id: str):
    _validate_doc_id(doc_id)
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
@limiter.limit("20/minute")
async def get_document_thumbnail(request: Request, doc_id: str):
    _validate_doc_id(doc_id)
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
            raise HTTPException(status_code=422, detail="PDF sin paginas")

        page = reader.pages[0]
        text = page.extract_text() or ""

        img = Image.new("RGB", (200, 280), "white")
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
            small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 10)
        except Exception:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
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
