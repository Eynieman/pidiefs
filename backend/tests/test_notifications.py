from unittest.mock import patch, MagicMock
from backend.services.notifications import notify_pdf_upload


class TestNotifyPdfUpload:
    @patch("backend.services.notifications.TWILIO_ACCOUNT_SID", "")
    @patch("backend.services.notifications.TWILIO_AUTH_TOKEN", "")
    @patch("backend.services.notifications.WHATSAPP_TO_NUMBER", "")
    @patch("backend.services.notifications.logger")
    def test_skips_when_credentials_missing(self, mock_logger):
        notify_pdf_upload("test.pdf", 10, 5, "abc123")
        mock_logger.warning.assert_called_once_with(
            "Twilio credentials not configured, skipping WhatsApp notification"
        )

    @patch("backend.services.notifications.httpx.post")
    @patch("backend.services.notifications.TWILIO_ACCOUNT_SID", "AC123")
    @patch("backend.services.notifications.TWILIO_AUTH_TOKEN", "auth_token")
    @patch("backend.services.notifications.WHATSAPP_TO_NUMBER", "+5491112345678")
    @patch("backend.services.notifications.logger")
    def test_sends_whatsapp_message(self, mock_logger, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        notify_pdf_upload("manual.pdf", 45, 12, "doc123")

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "AC123" in call_args[0][0]
        assert call_args[1]["auth"] == ("AC123", "auth_token")
        assert "manual.pdf" in call_args[1]["data"]["Body"]
        assert "45" in call_args[1]["data"]["Body"]
        assert "12" in call_args[1]["data"]["Body"]
        assert "doc123" in call_args[1]["data"]["Body"]
        mock_logger.info.assert_called_once()

    @patch("backend.services.notifications.httpx.post")
    @patch("backend.services.notifications.TWILIO_ACCOUNT_SID", "AC123")
    @patch("backend.services.notifications.TWILIO_AUTH_TOKEN", "auth_token")
    @patch("backend.services.notifications.WHATSAPP_TO_NUMBER", "+5491112345678")
    @patch("backend.services.notifications.logger")
    def test_handles_api_error_gracefully(self, mock_logger, mock_post):
        mock_post.side_effect = Exception("Connection timeout")

        notify_pdf_upload("test.pdf", 5, 2, "xyz789")

        mock_logger.error.assert_called_once()
        assert "Failed to send WhatsApp notification" in mock_logger.error.call_args[0][0]

    @patch("backend.services.notifications.httpx.post")
    @patch("backend.services.notifications.TWILIO_ACCOUNT_SID", "AC123")
    @patch("backend.services.notifications.TWILIO_AUTH_TOKEN", "auth_token")
    @patch("backend.services.notifications.WHATSAPP_TO_NUMBER", "+5491112345678")
    @patch("backend.services.notifications.logger")
    def test_message_format_contains_expected_fields(self, mock_logger, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        notify_pdf_upload("report.pdf", 100, 30, "abc123")

        body = mock_post.call_args[1]["data"]["Body"]
        assert "PDF subido en pidiefs" in body
        assert "report.pdf" in body
        assert "100" in body
        assert "30" in body
        assert "abc123" in body

    @patch("backend.services.notifications.httpx.post")
    @patch("backend.services.notifications.TWILIO_ACCOUNT_SID", "AC123")
    @patch("backend.services.notifications.TWILIO_AUTH_TOKEN", "auth_token")
    @patch("backend.services.notifications.WHATSAPP_TO_NUMBER", "+5491112345678")
    @patch("backend.services.notifications.logger")
    def test_message_from_and_to_correct(self, mock_logger, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        notify_pdf_upload("test.pdf", 1, 1, "id1")

        data = mock_post.call_args[1]["data"]
        assert data["From"] == "whatsapp:+14155238886"
        assert data["To"] == "whatsapp:+5491112345678"
