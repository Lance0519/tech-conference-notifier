from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import List, Dict, Any

from tech_conf_notifier.fetchers.base import BaseFetcher
from tech_conf_notifier.models import Conference

logger = logging.getLogger("tech_conf_notifier.fetchers.custom")


class CustomJsonFetcher(BaseFetcher):
    """
    Loads custom user-defined conferences from a local JSON file.
    Allows users to track regional events, internal conferences, or local meetups.
    """

    def __init__(self, json_path: str | Path = "custom_conferences.json"):
        self.json_path = Path(json_path)

    @property
    def name(self) -> str:
        return "custom"

    def fetch(self, start_date: date, end_date: date, topics: List[str] | None = None) -> List[Conference]:
        if not self.json_path.exists():
            return []

        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read custom conferences file {self.json_path}: {e}")
            return []

        if not isinstance(data, list):
            return []

        conferences: List[Conference] = []
        for item in data:
            try:
                name = item.get("name", "").strip()
                if not name:
                    continue

                raw_start = item.get("startDate") or item.get("start_date")
                if not raw_start:
                    continue
                conf_start = datetime.strptime(raw_start, "%Y-%m-%d").date()

                raw_end = item.get("endDate") or item.get("end_date")
                conf_end = None
                if raw_end:
                    try:
                        conf_end = datetime.strptime(raw_end, "%Y-%m-%d").date()
                    except ValueError:
                        pass

                effective_end = conf_end or conf_start
                if effective_end < start_date or conf_start > end_date:
                    continue

                topic = item.get("topic") or item.get("category") or "Information Technology"
                url = item.get("url", "")
                city = item.get("city") or "Not announced"
                country = item.get("country") or "Not announced"
                is_online = bool(item.get("online", False) or item.get("is_online", False))
                description = item.get("description") or "Not available"
                fee_type = item.get("fee_type", "unknown")
                fee_amount = item.get("fee_amount", "Not announced")
                fmt = "virtual" if is_online else item.get("format", "in_person")

                conf = Conference(
                    name=name,
                    category=topic,
                    source=self.name,
                    start_date=conf_start,
                    end_date=conf_end,
                    city=city,
                    country=country,
                    format=fmt,
                    url=url,
                    description=description,
                    fee_type=fee_type,
                    fee_amount=fee_amount,
                    metadata=item.get("metadata", {})
                )
                conferences.append(conf)
            except Exception as e:
                logger.debug(f"Skipping invalid custom conference entry: {e}")

        return conferences
