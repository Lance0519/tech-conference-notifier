from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List
from tech_conf_notifier.models import Conference


class BaseNotifier(ABC):
    """Abstract base class for notification dispatchers."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def notify(self, conferences: List[Conference]) -> bool:
        """
        Send notification for a list of conferences.
        :param conferences: List of upcoming conferences to alert the user about.
        :return: True if sent successfully, False otherwise.
        """
        pass

    @abstractmethod
    def test_notification(self) -> bool:
        """
        Send a test alert to verify this notification channel is configured properly.
        """
        pass
