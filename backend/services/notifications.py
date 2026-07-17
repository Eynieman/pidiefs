import os
import logging
import httpx

logger = logging.getLogger(__name__)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"
WHATSAPP_TO_NUMBER = os.getenv("WHATSAPP_TO_NUMBER", "")


def notify_pdf_upload(filename: str, pages: int, chunks: int, doc_id: str):
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, WHATSAPP_TO_NUMBER]):
        logger.warning("Twilio credentials not configured, skipping WhatsApp notification")
        return

    message = (
        f"\U0001f4c4 PDF subido en pidiefs\n"
        f"\n"
        f"\U0001f4c1 Archivo: {filename}\n"
        f"\U0001f4dd P\u00e1ginas: {pages}\n"
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
        logger.info(f"WhatsApp notification sent for {filename}")
    except Exception as e:
        logger.error(f"Failed to send WhatsApp notification: {e}")
