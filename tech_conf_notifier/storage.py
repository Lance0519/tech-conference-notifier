from __future__ import annotations

import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List, Optional
from tech_conf_notifier.models import Conference

logger = logging.getLogger("tech_conf_notifier.storage")


class NotificationTracker:
    """
    Tracks notified conferences to avoid duplicates while allowing
    smart reminder stages (e.g., first discovery, 7 days before, 1 day before).
    """

    def __init__(self, storage_path: str | Path = "seen_conferences.json"):
        self.storage_path = Path(storage_path)
        self.data: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if not self.storage_path.exists():
            return {}
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading {self.storage_path}, starting fresh: {e}")
            return {}

    def save(self) -> None:
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving seen conferences: {e}")

    def should_notify(self, conf: Conference, remind_days_before: List[int]) -> bool:
        """
        Determines whether the user should be alerted for this conference.
        - True if never notified before (initial discovery)
        - True if entering a reminder stage (e.g. 7 days or 1 day before) that hasn't been sent yet
        """
        entry = self.data.get(conf.id)
        if not entry:
            return True

        notified_stages = entry.get("notified_stages", [])
        days_until = conf.days_until

        for stage_day in remind_days_before:
            stage_key = f"reminder_{stage_day}d"
            # If we are within the threshold (e.g. <= 7 days) and haven't sent this reminder stage
            if 0 <= days_until <= stage_day and stage_key not in notified_stages:
                return True

        return False

    def mark_notified(self, conf: Conference, remind_days_before: List[int]) -> None:
        """Record that a notification was sent for this conference."""
        now_iso = datetime.now().isoformat()
        days_until = conf.days_until

        stages = []
        if conf.id in self.data:
            stages = self.data[conf.id].get("notified_stages", [])

        if "initial" not in stages:
            stages.append("initial")

        for stage_day in remind_days_before:
            stage_key = f"reminder_{stage_day}d"
            if 0 <= days_until <= stage_day and stage_key not in stages:
                stages.append(stage_key)

        self.data[conf.id] = {
            "name": conf.name,
            "start_date": conf.start_date.isoformat(),
            "first_seen": self.data.get(conf.id, {}).get("first_seen", now_iso),
            "last_notified": now_iso,
            "notified_stages": stages
        }

    def clear(self) -> None:
        self.data.clear()
        if self.storage_path.exists():
            self.storage_path.unlink()
