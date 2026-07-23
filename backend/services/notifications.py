import os
import logging
import httpx

logger = logging.getLogger(__name__)

CALLMEBOT_API_KEY = os.getenv("CALLMEBOT_API_KEY", "")
WHATSAPP_TO_NUMBER = os.getenv("WHATSAPP_TO_NUMBER", "")


def _send_whatsapp(message: str, log_label: str):
    if not all([CALLMEBOT_API_KEY, WHATSAPP_TO_NUMBER]):
        logger.warning("CallMeBot not configured, skipping WhatsApp notification")
        return

    try:
        url = "https://api.callmebot.com/whatsapp.php"
        params = {
            "phone": WHATSAPP_TO_NUMBER,
            "text": message,
            "apikey": CALLMEBOT_API_KEY,
        }
        response = httpx.get(url, params=params, timeout=10)
        response.raise_for_status()
        logger.info("WhatsApp notification sent for %s", log_label)
    except httpx.HTTPStatusError as e:
        logger.error("Error CallMeBot: %s - %s", e.response.status_code, e.response.text)
    except httpx.RequestError as e:
        logger.error("Error de conexion con CallMeBot: %s", e)
    except Exception as e:
        logger.error("Error inesperado al enviar notificacion WhatsApp: %s", e)


def notify_pdf_upload(filename: str, pages: int, chunks: int, doc_id: str):
    message = (
        f"\U0001f4c4 PDF subido en pageyn\n"
        f"\U0001f4c1 Archivo: {filename}\n"
        f"\U0001f4dd Paginas: {pages}\n"
        f"\U0001f9e9 Chunks: {chunks}\n"
        f"\U0001f194 ID: {doc_id}"
    )
    _send_whatsapp(message, filename)


def notify_pdf_deleted(filename: str, doc_id: str):
    message = (
        f"\U0001f5d1 PDF eliminado de pageyn\n"
        f"\U0001f4c1 Archivo: {filename}\n"
        f"\U0001f194 ID: {doc_id}"
    )
    _send_whatsapp(message, filename)


def notify_github_push(repo: str, branch: str, author: str,
                       commits: list[dict], compare_url: str):
    first_msg = commits[0]["message"].split("\n")[0] if commits else ""
    commit_count = len(commits)
    count_suffix = f" (+{commit_count - 1} mas)" if commit_count > 1 else ""

    message = (
        f"\U0001f4e6 Push a {repo} ({branch})\n"
        f"\U0001f464 {author}\n"
        f"\U0001f4dd \"{first_msg[:80]}\"{count_suffix}\n"
        f"\U0001f517 {compare_url}"
    )
    _send_whatsapp(message, f"push {repo} ({branch})")
