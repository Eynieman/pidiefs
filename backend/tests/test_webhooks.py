import hmac
import json
from unittest.mock import patch, MagicMock

from backend.routers.webhooks import _verify_signature


SECRET = "test_secret_123"


def _sign_payload(payload: bytes, secret: str = SECRET) -> str:
    return f"sha256={hmac.new(secret.encode(), payload, 'sha256').hexdigest()}"


PUSH_PAYLOAD = {
    "ref": "refs/heads/main",
    "pusher": {"name": "testuser"},
    "repository": {"full_name": "testowner/testrepo"},
    "commits": [
        {"message": "fix: resolve bug\n\nLong description", "url": "https://github.com/testowner/testrepo/commit/abc123"},
    ],
    "compare": "https://github.com/testowner/testrepo/compare/abc123...def456",
}


class TestVerifySignature:
    def test_valid_signature(self):
        payload = json.dumps(PUSH_PAYLOAD).encode()
        sig = _sign_payload(payload)
        assert _verify_signature(payload, sig, SECRET) is True

    def test_invalid_signature(self):
        payload = json.dumps(PUSH_PAYLOAD).encode()
        sig = "sha256=invalid"
        assert _verify_signature(payload, sig, SECRET) is False

    def test_no_secret_returns_false(self):
        payload = json.dumps(PUSH_PAYLOAD).encode()
        sig = _sign_payload(payload)
        assert _verify_signature(payload, sig, "") is False

    def test_wrong_secret_returns_false(self):
        payload = json.dumps(PUSH_PAYLOAD).encode()
        sig = _sign_payload(payload, secret="wrong_secret")
        assert _verify_signature(payload, sig, SECRET) is False


class TestGithubWebhook:
    async def test_missing_secret_returns_500(self, client, monkeypatch):
        monkeypatch.setattr("backend.routers.webhooks.GITHUB_WEBHOOK_SECRET", "")
        res = await client.post("/api/webhooks/github", json={})
        assert res.status_code == 500

    async def test_missing_signature_returns_400(self, client, monkeypatch):
        monkeypatch.setattr("backend.routers.webhooks.GITHUB_WEBHOOK_SECRET", SECRET)
        res = await client.post(
            "/api/webhooks/github",
            json={},
            headers={"x-github-event": "push"},
        )
        assert res.status_code == 400

    async def test_invalid_signature_returns_401(self, client, monkeypatch):
        monkeypatch.setattr("backend.routers.webhooks.GITHUB_WEBHOOK_SECRET", SECRET)
        res = await client.post(
            "/api/webhooks/github",
            json={},
            headers={
                "x-github-event": "push",
                "x-hub-signature-256": "sha256=invalid",
            },
        )
        assert res.status_code == 401

    async def test_non_push_event_ignored(self, client, monkeypatch):
        monkeypatch.setattr("backend.routers.webhooks.GITHUB_WEBHOOK_SECRET", SECRET)
        payload = json.dumps({}).encode()
        sig = _sign_payload(payload)

        res = await client.post(
            "/api/webhooks/github",
            content=payload,
            headers={
                "x-github-event": "ping",
                "x-hub-signature-256": sig,
                "content-type": "application/json",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ignored"
        assert data["event"] == "ping"

    @patch("backend.routers.webhooks.notify_github_push")
    async def test_push_event_triggers_notification(self, mock_notify, client, monkeypatch):
        monkeypatch.setattr("backend.routers.webhooks.GITHUB_WEBHOOK_SECRET", SECRET)
        payload = json.dumps(PUSH_PAYLOAD).encode()
        sig = _sign_payload(payload)

        res = await client.post(
            "/api/webhooks/github",
            content=payload,
            headers={
                "x-github-event": "push",
                "x-hub-signature-256": sig,
                "content-type": "application/json",
            },
        )
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

        mock_notify.assert_called_once_with(
            "testowner/testrepo", "main", "testuser",
            PUSH_PAYLOAD["commits"],
            PUSH_PAYLOAD["compare"],
        )

    async def test_push_event_sends_notification_end_to_end(self, client, monkeypatch):
        monkeypatch.setattr("backend.routers.webhooks.GITHUB_WEBHOOK_SECRET", SECRET)
        monkeypatch.setattr("backend.services.notifications.CALLMEBOT_API_KEY", "testkey")
        monkeypatch.setattr("backend.services.notifications.WHATSAPP_TO_NUMBER", "+549111")
        monkeypatch.setattr("backend.services.notifications.httpx.get", MagicMock())

        payload = json.dumps(PUSH_PAYLOAD).encode()
        sig = _sign_payload(payload)

        res = await client.post(
            "/api/webhooks/github",
            content=payload,
            headers={
                "x-github-event": "push",
                "x-hub-signature-256": sig,
                "content-type": "application/json",
            },
        )
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
