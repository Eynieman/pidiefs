import os
import logging
import httpx

logger = logging.getLogger(__name__)

CALLMEBOT_API_KEY = os.getenv("CALLMEBOT_API_KEY", "")
WHATSAPP_TO_NUMBER = os.getenv("WHATSAPP_TO_NUMBER", "")


def notify_pdf_upload(filename: str, pages: int, chunks: int, doc_id: str):
    if not all([CALLMEBOT_API_KEY, WHATSAPP_TO_NUMBER]):
        logger.warning("CallMeBot not configured, skipping WhatsApp notification")
        return

    message = (
        f"\U0001f4c4 PDF subido en pageyn\n"
        f"\U0001f4c1 Archivo: {filename}\n"
        f"\U0001f4dd Paginas: {pages}\n"
        f"\U0001f9e9 Chunks: {chunks}\n"
        f"\U0001f194 ID: {doc_id}"
    )

    try:
        url = "https://api.callmebot.com/whatsapp.php"
        params = {
            "phone": WHATSAPP_TO_NUMBER,
            "text": message,
            "apikey": CALLMEBOT_API_KEY,
        }
        response = httpx.get(url, params=params, timeout=10)
        response.raise_for_status()
        logger.info("WhatsApp notification sent for %s", filename)
    except httpx.HTTPStatusError as e:
        logger.error("Error CallMeBot: %s - %s", e.response.status_code, e.response.text)
    except httpx.RequestError as e:
        logger.error("Error de conexion con CallMeBot: %s", e)
    except Exception as e:
        logger.error("Error inesperado al enviar notificacion WhatsApp: %s", e)
