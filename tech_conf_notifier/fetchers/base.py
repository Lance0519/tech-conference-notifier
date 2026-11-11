from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import List
from tech_conf_notifier.models import Conference


class BaseFetcher(ABC):
    """Abstract base class for conference data fetchers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the fetcher source."""
        pass

    @abstractmethod
    def fetch(self, start_date: date, end_date: date, topics: List[str] | None = None) -> List[Conference]:
        """
        Fetch conferences occurring within the given date window.
        
        :param start_date: Starting date (inclusive)
        :param end_date: Ending date (inclusive)
        :param topics: Optional list of topic keywords or categories
        :return: List of Conference objects
        """
        pass
