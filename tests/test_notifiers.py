from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from tech_conf_notifier.models import Conference
from tech_conf_notifier.notifiers.desktop import DesktopToastNotifier
from tech_conf_notifier.notifiers.discord import DiscordNotifier
from tech_conf_notifier.notifiers.telegram import TelegramNotifier
from tech_conf_notifier.notifiers.email_smtp import EmailNotifier
from tech_conf_notifier.notifiers.digest import DigestNotifier


class TestNotifiers:
    """Test suite for desktop toast, Discord, Telegram, Email, and Digest notifiers."""

    def test_desktop_toast_notifier(self, sample_conferences: list[Conference]):
        notifier = DesktopToastNotifier(app_name="Test Notifier", max_toasts=2)
        assert notifier.name == "desktop"

        # Mock windows_toasts
        mock_toaster = MagicMock()
        mock_toast_cls = MagicMock()

        with patch.dict("sys.modules", {"windows_toasts": MagicMock(WindowsToaster=MagicMock(return_value=mock_toaster), Toast=mock_toast_cls)}):
            # Empty list
            assert notifier.notify([]) is True
            mock_toaster.show_toast.assert_not_called()

            # Multiple conferences (> max_toasts triggers summary)
            success = notifier.notify(sample_conferences)
            assert success is True
            # max_toasts=2 + 1 summary toast = 3 calls
            assert mock_toaster.show_toast.call_count == 3

            # Test notification
            mock_toaster.reset_mock()
            assert notifier.test_notification() is True
            assert mock_toaster.show_toast.call_count == 1

    def test_desktop_toast_error_handling(self, sample_conferences: list[Conference]):
        notifier = DesktopToastNotifier()
        mock_wt = MagicMock()
        mock_wt.WindowsToaster.side_effect = Exception("Toaster Error")
        with patch.dict("sys.modules", {"windows_toasts": mock_wt}):
            # Should catch exception and return False
            assert notifier.notify(sample_conferences) is False

    @patch("urllib.request.urlopen")
    def test_discord_notifier_payload_and_chunking(self, mock_urlopen, sample_conferences: list[Conference], mock_http_response):
        mock_urlopen.return_value = mock_http_response(status=204)
        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/123/abc", mention_role="12345")
        assert notifier.name == "discord"

        # Missing webhook
        assert DiscordNotifier(webhook_url="").notify(sample_conferences) is False

        # Dispatch
        success = notifier.notify(sample_conferences)
        assert success is True
        assert mock_urlopen.call_count >= 1

        # Check payload structure
        call_args = mock_urlopen.call_args[0]
        req = call_args[0]
        data = json.loads(req.data.decode("utf-8"))
        assert "embeds" in data
        assert len(data["embeds"]) <= 5
        assert "<@&12345>" in data.get("content", "")

        first_embed = data["embeds"][0]
        assert "title" in first_embed
        assert "fields" in first_embed
        assert any(f["name"] == "📅 Dates" for f in first_embed["fields"])

        # Test notification
        assert notifier.test_notification() is True

    @patch("urllib.request.urlopen")
    def test_telegram_notifier(self, mock_urlopen, sample_conferences: list[Conference], mock_http_response):
        mock_urlopen.return_value = mock_http_response(status=200, body=json.dumps({"ok": True}))
        notifier = TelegramNotifier(bot_token="fake_bot_token", chat_id="999888")
        assert notifier.name == "telegram"

        # Missing token
        assert TelegramNotifier(bot_token="", chat_id="").notify(sample_conferences) is False

        # Dispatch
        success = notifier.notify(sample_conferences)
        assert success is True
        assert mock_urlopen.call_count == len(sample_conferences[:10])

        call_args = mock_urlopen.call_args[0]
        req = call_args[0]
        data = json.loads(req.data.decode("utf-8"))
        assert data["chat_id"] == "999888"
        assert data["parse_mode"] == "HTML"
        assert "reply_markup" in data
        assert "inline_keyboard" in data["reply_markup"]

        # Test notification
        assert notifier.test_notification() is True

    @patch("smtplib.SMTP")
    def test_email_notifier(self, mock_smtp_cls, sample_conferences: list[Conference]):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        notifier = EmailNotifier(
            smtp_server="smtp.example.com",
            smtp_port=587,
            sender_email="sender@example.com",
            sender_password="secretpassword",
            recipient_email="recipient@example.com",
            use_tls=True
        )
        assert notifier.name == "email"

        # Missing credentials returns False
        assert EmailNotifier().notify(sample_conferences) is False

        # Dispatch
        success = notifier.notify(sample_conferences)
        assert success is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("sender@example.com", "secretpassword")
        assert mock_server.sendmail.call_count == 1

        # Test notification
        assert notifier.test_notification() is True

    def test_digest_notifier_html_and_markdown(self, tmp_path: Path, sample_conferences: list[Conference]):
        html_file = tmp_path / "digest.html"
        md_file = tmp_path / "digest.md"

        notifier = DigestNotifier(output_html=str(html_file), output_markdown=str(md_file))
        assert notifier.name == "digest"

        success = notifier.notify(sample_conferences)
        assert success is True
        assert html_file.exists()
        assert md_file.exists()

        # Check Markdown content
        md_content = md_file.read_text(encoding="utf-8")
        assert "# 🔔 Upcoming IT, Computer Science & Technology Conferences" in md_content
        assert "| Event Name | Category | Date | Location | Format | Status | Official Link |" in md_content
        for c in sample_conferences:
            assert c.name in md_content
            assert c.category in md_content

        # Check HTML content
        html_content = html_file.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in html_content
        assert "Upcoming IT, Computer Science & Tech Conferences" in html_content
        assert "id=\"searchInput\"" in html_content
        assert "class=\"card\"" in html_content
        for c in sample_conferences:
            assert c.name in html_content

        # Test notification
        assert notifier.test_notification() is True
