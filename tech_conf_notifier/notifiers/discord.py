from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from typing import List

from tech_conf_notifier.models import Conference
from tech_conf_notifier.notifiers.base import BaseNotifier

logger = logging.getLogger("tech_conf_notifier.notifiers.discord")

# Color palette for Discord embeds
CATEGORY_COLORS = {
    "Artificial Intelligence and Machine Learning": 0x9B59B6,  # Purple
    "Cybersecurity": 0xE74C3C,                                # Red
    "Cloud Computing and DevOps": 0x3498DB,                   # Blue
    "Software Engineering": 0x2ECC71,                         # Green
    "Data Science and Analytics": 0x1ABC9C,                   # Teal
    "Web and Mobile Development": 0xF39C12,                   # Orange
    "Computer Science": 0x34495E,                             # Slate
}


class DiscordNotifier(BaseNotifier):
    """Dispatches rich embed notifications to a Discord Webhook."""

    def __init__(self, webhook_url: str, mention_role: str | None = None):
        self.webhook_url = webhook_url
        self.mention_role = mention_role

    @property
    def name(self) -> str:
        return "discord"

    def notify(self, conferences: List[Conference]) -> bool:
        if not self.webhook_url or not conferences:
            return False

        # Bundle in groups of up to 5 embeds per webhook message
        chunks = [conferences[i:i + 5] for i in range(0, len(conferences), 5)]

        for chunk in chunks:
            embeds = []
            for conf in chunk:
                color = CATEGORY_COLORS.get(conf.category, 0x5865F2)
                flag = "🇵🇭 " if conf.is_philippines else "🌐 "
                fields = [
                    {"name": "📅 Dates", "value": f"{conf.formatted_date_range}\n*({conf.status_label})*", "inline": True},
                    {"name": "📍 Location", "value": f"{flag}{conf.location_str}", "inline": True},
                    {"name": "🏷️ Domain", "value": conf.category, "inline": True},
                ]
                if conf.cfp_deadline:
                    fields.append({"name": "📝 CFP Deadline", "value": conf.cfp_deadline.strftime("%b %d, %Y"), "inline": True})
                if conf.fee_amount and conf.fee_amount != "Not announced":
                    fields.append({"name": "🎟️ Admission", "value": conf.fee_amount, "inline": True})

                desc = conf.description if conf.description != "Not available" else "Official tech conference and convention."
                if len(desc) > 250:
                    desc = desc[:247] + "..."

                embed = {
                    "title": f"🔔 {conf.name}",
                    "url": conf.url,
                    "description": desc,
                    "color": color,
                    "fields": fields,
                    "footer": {"text": f"Source: {conf.source} | Tech Conference Notifier"}
                }
                embeds.append(embed)

            payload = {"embeds": embeds}
            if self.mention_role:
                payload["content"] = f"<@&{self.mention_role}> New upcoming tech events discovered!"

            try:
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    self.webhook_url,
                    data=data,
                    headers={"Content-Type": "application/json", "User-Agent": "TechConferenceNotifier/1.0"}
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status not in (200, 204):
                        logger.warning(f"Discord webhook returned status {resp.status}")
                        return False
            except Exception as e:
                logger.error(f"Failed to dispatch Discord webhook: {e}")
                return False

        return True

    def test_notification(self) -> bool:
        if not self.webhook_url:
            return False

        payload = {
            "embeds": [{
                "title": "✅ Tech Conference Notifier Webhook Active",
                "description": "Discord notifications are successfully configured and ready to alert you to upcoming IT/CS conferences!",
                "color": 0x2ECC71,
                "footer": {"text": "Tech Conference Notifier"}
            }]
        }
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json", "User-Agent": "TechConferenceNotifier/1.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status in (200, 204)
        except Exception as e:
            logger.error(f"Discord test alert failed: {e}")
            return False
