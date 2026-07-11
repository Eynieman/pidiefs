from groq import Groq
from backend.config import GROQ_API_KEY, GROQ_MODEL

_client = None


def get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def generate_answer(question: str, context_docs: list[dict]) -> str:
    client = get_client()

    context = "\n\n---\n\n".join(
        f"[Fuente: {doc['metadata'].get('source', 'desconocido')}, "
        f"Página {doc['metadata'].get('page', '?')}]\n{doc['content']}"
        for doc in context_docs
    )

    messages = [
        {
            "role": "system",
            "content": (
                "Eres un asistente experto en análisis de documentos. "
                "Responde la pregunta del usuario basándote ÚNICAMENTE en el contexto proporcionado. "
                "Si la información no está en el contexto, di que no lo encuentras. "
                "Cita las fuentes (nombre de archivo y página) cuando sea posible. "
                "Responde en el mismo idioma que la pregunta."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Contexto de los documentos:\n\n{context}\n\n"
                f"Pregunta: {question}"
            ),
        },
    ]

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=2048,
    )

    return response.choices[0].message.content
