from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from typing import List

from tech_conf_notifier.models import Conference
from tech_conf_notifier.notifiers.base import BaseNotifier

logger = logging.getLogger("tech_conf_notifier.notifiers.telegram")


class TelegramNotifier(BaseNotifier):
    """Dispatches notifications to a Telegram chat via Bot API."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    @property
    def name(self) -> str:
        return "telegram"

    def notify(self, conferences: List[Conference]) -> bool:
        if not self.bot_token or not self.chat_id or not conferences:
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        for conf in conferences[:10]:
            flag = "🇵🇭 " if conf.is_philippines else "🌐 "
            text = (
                f"🔔 <b>{conf.name}</b>\n\n"
                f"🏷️ <b>Category:</b> {conf.category}\n"
                f"📅 <b>Dates:</b> {conf.formatted_date_range} (<i>{conf.status_label}</i>)\n"
                f"📍 <b>Location:</b> {flag}{conf.location_str}\n"
            )
            if conf.organizer and conf.organizer != "Not announced":
                text += f"🏢 <b>Organizer:</b> {conf.organizer}\n"
            if conf.cfp_deadline:
                text += f"📝 <b>CFP Closes:</b> {conf.cfp_deadline.strftime('%b %d, %Y')}\n"

            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            }
            if conf.url:
                payload["reply_markup"] = {
                    "inline_keyboard": [[
                        {"text": "🌐 Open Event Website", "url": conf.url}
                    ]]
                }

            try:
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status != 200:
                        logger.warning(f"Telegram returned status {resp.status}")
                        return False
            except Exception as e:
                logger.error(f"Failed to send Telegram message: {e}")
                return False

        return True

    def test_notification(self) -> bool:
        if not self.bot_token or not self.chat_id:
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": "✅ <b>Tech Conference Notifier Active</b>\n\nTelegram notifications are working properly!",
            "parse_mode": "HTML"
        }
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"Telegram test message failed: {e}")
            return False
