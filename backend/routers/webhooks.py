import hmac
import os
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from backend.services.notifications import notify_github_push
from backend.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")


def _verify_signature(payload: bytes, signature_header: str, secret: str) -> bool:
    if not secret:
        return False
    expected = hmac.new(secret.encode(), payload, "sha256").hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature_header)


@router.post("/github")
@limiter.limit("30/minute")
async def github_webhook(request: Request):
    if not GITHUB_WEBHOOK_SECRET:
        logger.warning("GITHUB_WEBHOOK_SECRET not configured")
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    signature = request.headers.get("x-hub-signature-256", "")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing x-hub-signature-256 header")

    payload = await request.body()
    if not _verify_signature(payload, signature, GITHUB_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = request.headers.get("x-github-event", "")
    if event != "push":
        return {"status": "ignored", "event": event}

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    repo = body.get("repository", {}).get("full_name", "unknown")
    ref = body.get("ref", "")
    branch = ref.replace("refs/heads/", "") if ref else "unknown"
    author = body.get("pusher", {}).get("name", "unknown")
    commits = body.get("commits", [])
    compare_url = body.get("compare", "")

    notify_github_push(repo, branch, author, commits, compare_url)
    return {"status": "ok"}
