from __future__ import annotations

import logging
from typing import List

from tech_conf_notifier.models import Conference
from tech_conf_notifier.notifiers.base import BaseNotifier

logger = logging.getLogger("tech_conf_notifier.notifiers.desktop")


class DesktopToastNotifier(BaseNotifier):
    """
    Sends native desktop toast notifications on Windows 10/11 using windows-toasts.
    Includes clickable action buttons to open the conference URL directly.
    """

    def __init__(self, app_name: str = "Tech Conference Notifier", max_toasts: int = 5):
        self.app_name = app_name
        self.max_toasts = max_toasts

    @property
    def name(self) -> str:
        return "desktop"

    def notify(self, conferences: List[Conference]) -> bool:
        if not conferences:
            return True

        try:
            from windows_toasts import WindowsToaster, Toast

            toaster = WindowsToaster(self.app_name)
            to_send = conferences[:self.max_toasts]

            for conf in to_send:
                title = f"🔔 {conf.category}: {conf.name}"
                body = (
                    f"📅 {conf.formatted_date_range} ({conf.status_label})\n"
                    f"📍 {conf.location_str}"
                )
                toast = Toast([title, body])
                if conf.url:
                    toast.launch_action = conf.url

                toaster.show_toast(toast)

            # If more than max_toasts, send summary
            if len(conferences) > self.max_toasts:
                remaining = len(conferences) - self.max_toasts
                summary = Toast([
                    f"🔔 +{remaining} More Tech Conferences Discovered",
                    "Check the mobile app or upcoming conferences digest for the full list!"
                ])
                toaster.show_toast(summary)

            return True
        except Exception as e:
            logger.error(f"Failed to display desktop toast: {e}")
            return False

    def test_notification(self) -> bool:
        try:
            from windows_toasts import WindowsToaster, Toast

            toaster = WindowsToaster(self.app_name)
            toast = Toast([
                "🔔 Tech Conference Notifier Active",
                "Desktop notifications are successfully configured and working!"
            ])
            toast.launch_action = "https://github.com"
            toaster.show_toast(toast)
            return True
        except Exception as e:
            logger.error(f"Test notification failed: {e}")
            return False
