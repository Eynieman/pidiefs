import logging

import httpx

from backend.config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)


def generate_pdf_summary(filename: str, content: str) -> str:
    if not GROQ_API_KEY:
        return ""

    truncated = content[:3000]

    prompt = (
        "Eres un asistente de documentación. "
        "Resume el siguiente documento PDF en 3-5 oraciones clave. "
        "Sé conciso y preciso. Responde solo con el resumen, sin explicaciones adicionales.\n\n"
        f"Documento: {filename}\n"
        f"Contenido (primeras páginas):\n{truncated}"
    )

    try:
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 300,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"Failed to generate summary for {filename}: {e}")
        return ""
