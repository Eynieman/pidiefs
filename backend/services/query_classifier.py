import re
import logging

from backend.config import GROQ_API_KEY, GROQ_MODEL
from backend.services.llm import get_client

logger = logging.getLogger(__name__)

PATRONES_GLOBALES = re.compile(
    r"(resum(e|en|ir|a)|panorama|visi[óo]n\s*general|puntos\s*(m[aá]s\s*)?(importantes|clave|cr[ií]ticos)"
    r"|[ií]ndice|esquema|estructura|todo\s*(el\s*)?documento|completo|contenido\s*principal"
    r"|en\s*general|global|de\s*principio\s*a\s*fin|principales\s*(temas|puntos)"
    r"|s[ií]ntesis|cuadro\s*general|macro|a\s*grandes\s*rasgos|sobrevuelo"
    r")",
    re.IGNORECASE,
)

PATRONES_LOCALES = re.compile(
    r"(p[aá]gina\s*\d+|secci[oó]n\s*\d+|cl[aá]usula|art[ií]culo|p[aá]rrafo"
    r"|qu[eé]\s*dice|cu[aá]l\s*es\s*el|d[oó]nde[-\s]|cu[aá]ndo"
    r"|n[uú]mero\s*\d+|literal|inciso|anexo"
    r")",
    re.IGNORECASE,
)

PATRONES_LOCALES_EXACTOS = re.compile(
    r"^\s*(?:qu[eé]\s*(?:es|significa|contiene|dice|opinas|piensas)"
    r"|d[oó]nde\s+est[aá]|c[oó]mo\s+se\s+(?:define|llama|conoce)"
    r"|cu[aá]l\s+es\s+la\s+diferencia|expl[ií]ca\s+la\s+(?:secci[oó]n|cl[aá]usula|p[aá]gina))",
    re.IGNORECASE,
)


def _score_patterns(question: str) -> tuple[float, float]:
    global_score = 0.0
    local_score = 0.0

    if PATRONES_GLOBALES.search(question):
        global_score += 0.45

    if PATRONES_LOCALES_EXACTOS.match(question):
        local_score += 0.5

    local_matches = PATRONES_LOCALES.findall(question)
    local_score += len(local_matches) * 0.2

    if len(question.split()) <= 5 and "?" in question:
        global_score += 0.15

    if len(question) > 100:
        local_score += 0.1

    return global_score, local_score


def _llm_classify(question: str) -> dict:
    if not GROQ_API_KEY:
        return {"type": "local", "confidence": 0.0, "method": "fallback_no_llm"}

    try:
        client = get_client()
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Clasifica esta pregunta en UNA palabra: local, hybrid, o global.\n"
                        "- local: pregunta sobre un detalle específico (página, cláusula, cifra, fecha)\n"
                        "- global: pregunta panorámica (resumen, temas principales, visión general)\n"
                        "- hybrid: pregunta que mezcla lo específico con contexto general\n"
                        "Responde SOLO con la palabra, sin explicación."
                    ),
                },
                {"role": "user", "content": question[:500]},
            ],
            temperature=0.0,
            max_tokens=5,
        )
        result = response.choices[0].message.content.strip().lower()
        if result in ("local", "hybrid", "global"):
            return {"type": result, "confidence": 0.5, "method": "llm"}
        logger.warning("LLM returned unexpected classification: %s", result)
    except Exception as e:
        logger.warning("LLM classification failed: %s", e)

    return {"type": "local", "confidence": 0.0, "method": "fallback_error"}


def classify_query(question: str) -> dict:
    global_score, local_score = _score_patterns(question)
    confidence = global_score - local_score

    logger.debug(
        "Query classification scores - global: %.2f, local: %.2f, net: %.2f",
        global_score,
        local_score,
        confidence,
    )

    if abs(confidence) >= 0.6:
        qtype = "global" if confidence > 0 else "local"
        return {"type": qtype, "confidence": abs(confidence), "method": "rule"}

    llm_result = _llm_classify(question)
    return llm_result


def get_retrieval_strategy(query_type: str) -> dict:
    strategies = {
        "local": {
            "levels": [0],
            "top_k": 5,
            "prompt_key": "local",
            "description": "búsqueda en chunks detallados",
        },
        "hybrid": {
            "levels": [0, 1],
            "top_k": 8,
            "prompt_key": "hybrid",
            "description": "búsqueda combinada chunks + resúmenes de sección",
        },
        "global": {
            "levels": [1, 2],
            "top_k": 8,
            "prompt_key": "global",
            "description": "búsqueda en resúmenes ejecutivos",
        },
    }
    return strategies.get(query_type, strategies["local"])
