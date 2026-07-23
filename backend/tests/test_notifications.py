import httpx
from unittest.mock import patch, MagicMock
from backend.services.notifications import notify_pdf_upload, notify_github_push


class TestNotifyPdfUpload:
    @patch("backend.services.notifications.CALLMEBOT_API_KEY", "")
    @patch("backend.services.notifications.WHATSAPP_TO_NUMBER", "")
    @patch("backend.services.notifications.logger")
    def test_skips_when_credentials_missing(self, mock_logger, *_):
        notify_pdf_upload("test.pdf", 10, 5, "abc123")
        mock_logger.warning.assert_called_once_with(
            "CallMeBot not configured, skipping WhatsApp notification"
        )

    @patch("backend.services.notifications.httpx.get")
    @patch("backend.services.notifications.CALLMEBOT_API_KEY", "apikey123")
    @patch("backend.services.notifications.WHATSAPP_TO_NUMBER", "+5491112345678")
    @patch("backend.services.notifications.logger")
    def test_sends_whatsapp_message(self, mock_logger, mock_get, *_):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        notify_pdf_upload("manual.pdf", 45, 12, "doc123")

        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]["params"]["phone"] == "+5491112345678"
        assert call_args[1]["params"]["apikey"] == "apikey123"
        assert "manual.pdf" in call_args[1]["params"]["text"]
        assert "45" in call_args[1]["params"]["text"]
        assert "12" in call_args[1]["params"]["text"]
        assert "doc123" in call_args[1]["params"]["text"]
        mock_logger.info.assert_called_once()

    @patch("backend.services.notifications.httpx.get")
    @patch("backend.services.notifications.CALLMEBOT_API_KEY", "apikey123")
    @patch("backend.services.notifications.WHATSAPP_TO_NUMBER", "+5491112345678")
    @patch("backend.services.notifications.logger")
    def test_handles_api_error_gracefully(self, mock_logger, mock_get, *_):
        mock_get.side_effect = httpx.RequestError("Connection timeout")

        notify_pdf_upload("test.pdf", 5, 2, "xyz789")

        mock_logger.error.assert_called_once()
        assert "Error de conexion con CallMeBot" in mock_logger.error.call_args[0][0]

    @patch("backend.services.notifications.httpx.get")
    @patch("backend.services.notifications.CALLMEBOT_API_KEY", "apikey123")
    @patch("backend.services.notifications.WHATSAPP_TO_NUMBER", "+5491112345678")
    @patch("backend.services.notifications.logger")
    def test_message_format_contains_expected_fields(self, mock_logger, mock_get, *_):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        notify_pdf_upload("report.pdf", 100, 30, "abc123")

        text = mock_get.call_args[1]["params"]["text"]
        assert "PDF subido en pageyn" in text
        assert "report.pdf" in text
        assert "100" in text
        assert "30" in text
        assert "abc123" in text

    @patch("backend.services.notifications.httpx.get")
    @patch("backend.services.notifications.CALLMEBOT_API_KEY", "apikey123")
    @patch("backend.services.notifications.WHATSAPP_TO_NUMBER", "+5491112345678")
    @patch("backend.services.notifications.logger")
    def test_params_have_correct_structure(self, mock_logger, mock_get, *_):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        notify_pdf_upload("test.pdf", 1, 1, "id1")

        params = mock_get.call_args[1]["params"]
        assert params["phone"] == "+5491112345678"
        assert params["apikey"] == "apikey123"
        assert "PDF subido" in params["text"]


class TestNotifyGithubPush:
    COMMITS = [
        {"message": "fix: resolve auth bug\n\nLong description"},
    ]

    @patch("backend.services.notifications.CALLMEBOT_API_KEY", "")
    @patch("backend.services.notifications.WHATSAPP_TO_NUMBER", "")
    @patch("backend.services.notifications.logger")
    def test_skips_when_credentials_missing(self, mock_logger, *_):
        notify_github_push("repo", "main", "user", self.COMMITS, "https://compare")
        mock_logger.warning.assert_called_once_with(
            "CallMeBot not configured, skipping WhatsApp notification"
        )

    @patch("backend.services.notifications.httpx.get")
    @patch("backend.services.notifications.CALLMEBOT_API_KEY", "apikey123")
    @patch("backend.services.notifications.WHATSAPP_TO_NUMBER", "+5491112345678")
    @patch("backend.services.notifications.logger")
    def test_sends_push_notification(self, mock_logger, mock_get, *_):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        notify_github_push("testowner/testrepo", "main", "testuser",
                           self.COMMITS, "https://compare")

        mock_get.assert_called_once()
        text = mock_get.call_args[1]["params"]["text"]
        assert "Push a testowner/testrepo" in text
        assert "(main)" in text
        assert "testuser" in text
        assert "fix: resolve auth bug" in text
        assert "https://compare" in text
        mock_logger.info.assert_called_once()

    @patch("backend.services.notifications.httpx.get")
    @patch("backend.services.notifications.CALLMEBOT_API_KEY", "apikey123")
    @patch("backend.services.notifications.WHATSAPP_TO_NUMBER", "+5491112345678")
    @patch("backend.services.notifications.logger")
    def test_multiple_commits_shows_count(self, mock_logger, mock_get, *_):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        commits = [
            {"message": "feat: add feature"},
            {"message": "fix: fix bug"},
            {"message": "chore: cleanup"},
        ]
        notify_github_push("repo", "main", "user", commits, "https://compare")

        text = mock_get.call_args[1]["params"]["text"]
        assert "feat: add feature" in text
        assert "(+2 mas)" in text
