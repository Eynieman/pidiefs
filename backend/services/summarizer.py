import logging

from backend.config import GROQ_API_KEY, GROQ_MODEL
from backend.services.llm import get_client

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
        client = get_client()
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Failed to generate summary for {filename}: {e}")
        return ""
