import logging

from backend.config import GROQ_API_KEY, GROQ_MODEL, SUMMARY_GLOBAL_SAMPLE_CHARS, SUMMARY_MAX_SECTIONS
from backend.services.llm import get_client
from backend.services.cache import pdf_summary_cache, make_summary_key

logger = logging.getLogger(__name__)


def _call_groq(prompt: str, max_tokens: int = 300) -> str:
    if not GROQ_API_KEY:
        return ""
    try:
        client = get_client()
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error("Groq call failed: %s", e)
        return ""


def generate_pdf_summary(filename: str, content: str) -> str:
    key = make_summary_key(filename, content)
    cached = pdf_summary_cache.get(key)
    if cached is not None:
        logger.info("Cache hit for generate_pdf_summary: %s", filename)
        return cached
    truncated = content[:3000]
    prompt = (
        "Eres un asistente de documentacion. "
        "Resume el siguiente documento PDF en 3-5 oraciones clave. "
        "Se conciso y preciso. Responde solo con el resumen, sin explicaciones adicionales.\n\n"
        f"Documento: {filename}\n"
        f"Contenido (primeras paginas):\n{truncated}"
    )
    result = _call_groq(prompt, max_tokens=300)
    pdf_summary_cache[key] = result
    return result


def summarize_cluster(texts: list[str], cluster_id: int) -> dict:
    combined = "\n\n---\n\n".join(texts)
    if len(combined) > 6000:
        combined = combined[:6000] + "\n\n[...]"

    prompt = (
        "Analiza estos fragmentos de un documento. "
        "Identifica el tema comun y genera:\n"
        "1. Un TITULO corto (max 6 palabras) para esta seccion tematica\n"
        "2. Un RESUMEN de 2-3 oraciones que capture los puntos clave\n\n"
        "Formato exacto:\n"
        "Titulo: <titulo>\n"
        "Resumen: <resumen>\n\n"
        f"Fragmentos:\n{combined}"
    )

    result = _call_groq(prompt, max_tokens=300)
    if not result:
        return {
            "content": f"[Seccion {cluster_id + 1}]\nNo se pudo generar resumen.",
            "title": f"Seccion {cluster_id + 1}",
            "cluster_id": cluster_id,
        }

    lines = result.split("\n", 2)
    title = f"Seccion {cluster_id + 1}"
    summary = result

    for line in lines:
        if line.lower().startswith("titulo") or line.lower().startswith("título"):
            title = line.split(":", 1)[1].strip() if ":" in line else title
        elif line.lower().startswith("resumen"):
            summary = line.split(":", 1)[1].strip() if ":" in line else summary
            break

    full_content = f"[{title}]\n{summary}"
    return {
        "content": full_content,
        "title": title,
        "summary": summary,
        "cluster_id": cluster_id,
    }


def generate_global_summary_enhanced(filename: str, pages: list[dict], section_summaries: list[dict] | None = None) -> str:
    total_chars = sum(len(p["content"]) for p in pages)

    if section_summaries:
        summaries_text = "\n\n".join(
            f"Seccion: {s.get('title', f'Seccion {i+1}')}\n{s.get('summary', s['content'])}"
            for i, s in enumerate(section_summaries)
        )
        prompt = (
            "Eres un asistente de documentacion. "
            "Genera un resumen ejecutivo de este PDF basandote en los resumenes "
            "de cada seccion. Incluye: proposito del documento, temas principales "
            "tratados, y conclusiones clave. Responde en 5-7 puntos.\n\n"
            f"Documento: {filename}\n\n"
            f"Resumenes de secciones:\n{summaries_text}"
        )
        return _call_groq(prompt, max_tokens=500)

    sample_chars = min(SUMMARY_GLOBAL_SAMPLE_CHARS, total_chars)
    beg = pages[0]["content"][: sample_chars // 3] if pages else ""

    mid_idx = len(pages) // 2
    mid = pages[mid_idx]["content"][: sample_chars // 3] if len(pages) > 2 else ""

    end = pages[-1]["content"][: sample_chars // 3] if len(pages) > 1 else ""

    sampled = f"[INICIO DEL DOCUMENTO]\n{beg}\n\n[MEDIO DEL DOCUMENTO]\n{mid}\n\n[FINAL DEL DOCUMENTO]\n{end}"

    prompt = (
        "Eres un asistente de documentacion. "
        "Genera un resumen ejecutivo de este PDF en 5-7 puntos clave. "
        "Incluye: proposito del documento, temas principales, "
        "y conclusiones mas importantes. Responde solo con el resumen.\n\n"
        f"Documento: {filename}\n\n"
        f"Contenido muestreado:\n{sampled}"
    )
    return _call_groq(prompt, max_tokens=500)
