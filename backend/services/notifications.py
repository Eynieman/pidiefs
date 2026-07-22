import os
import time
import logging
import httpx

logger = logging.getLogger(__name__)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"
WHATSAPP_TO_NUMBER = os.getenv("WHATSAPP_TO_NUMBER", "")

DAILY_LIMIT = 50
_daily_count = 0
_daily_reset = 0.0


def _check_quota() -> bool:
    global _daily_count, _daily_reset
    now = time.time()
    if now - _daily_reset > 86400:
        _daily_count = 0
        _daily_reset = now
    if _daily_count >= DAILY_LIMIT:
        remaining_time = int(86400 - (now - _daily_reset))
        logger.warning(
            "Limite diario de Twilio alcanzado (%d/%d). Se reanudara en ~%d minutos.",
            _daily_count, DAILY_LIMIT, remaining_time // 60,
        )
        return False
    return True


def _increment_quota():
    global _daily_count
    _daily_count += 1


def notify_pdf_upload(filename: str, pages: int, chunks: int, doc_id: str):
    if not _check_quota():
        return

    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, WHATSAPP_TO_NUMBER]):
        logger.warning("Twilio credentials not configured, skipping WhatsApp notification")
        return

    message = (
        f"\U0001f4c4 PDF subido en pidiefs\n"
        f"\n"
        f"\U0001f4c1 Archivo: {filename}\n"
        f"\U0001f4dd Paginas: {pages}\n"
        f"\U0001f9e9 Chunks: {chunks}\n"
        f"\U0001f194 ID: {doc_id}"
    )

    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
        data = {
            "Body": message,
            "From": TWILIO_WHATSAPP_FROM,
            "To": f"whatsapp:{WHATSAPP_TO_NUMBER}",
        }
        response = httpx.post(url, data=data, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), timeout=10)
        response.raise_for_status()
        _increment_quota()
        logger.info("WhatsApp notification sent for %s (%d/%d)", filename, _daily_count, DAILY_LIMIT)
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        if status == 429:
            logger.error(
                "Cuota diaria de Twilio excedida (%d/%d). Proximo envio cuando se resetee el contador.",
                _daily_count, DAILY_LIMIT,
            )
        elif status == 401:
            logger.error("Credenciales Twilio invalidas. Verifica TWILIO_ACCOUNT_SID y TWILIO_AUTH_TOKEN.")
        else:
            logger.error("Error HTTP de Twilio: %s - %s", status, e.response.text)
    except httpx.RequestError as e:
        logger.error("Error de conexion con Twilio: %s", e)
    except Exception as e:
        logger.error("Error inesperado al enviar notificacion WhatsApp: %s", e)
