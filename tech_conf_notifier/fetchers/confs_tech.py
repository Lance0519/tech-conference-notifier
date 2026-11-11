from __future__ import annotations

import json
import logging
import time
from datetime import date, datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import urllib.request
import urllib.error

from tech_conf_notifier.fetchers.base import BaseFetcher
from tech_conf_notifier.models import Conference
from tech_conf_notifier.classifier import EventClassifier

logger = logging.getLogger("tech_conf_notifier.fetchers.confs_tech")

ALL_CONFS_TECH_TOPICS = [
    "general", "security", "devops", "data", "python", "javascript",
    "typescript", "android", "ios", "golang", "rust", "cpp", "java",
    "dotnet", "networking", "iot", "ux", "leadership", "testing",
    "performance", "opensource", "api"
]


class ConfsTechFetcher(BaseFetcher):
    """
    Fetches curated IT & developer conference data from the open-source
    'tech-conferences/conference-data' repository on GitHub.
    """

    BASE_URL = "https://raw.githubusercontent.com/tech-conferences/conference-data/main/conferences/{year}/{topic}.json"

    def __init__(self, cache_dir: str | Path = ".cache/confs_tech", cache_ttl_hours: int = 12):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl_seconds = cache_ttl_hours * 3600

    @property
    def name(self) -> str:
        return "confs.tech"

    def _get_cached_or_download(self, year: int, topic: str) -> Optional[List[Dict[str, Any]]]:
        cache_file = self.cache_dir / f"{year}_{topic}.json"

        # Check if fresh in cache
        if cache_file.exists():
            age = time.time() - cache_file.stat().st_mtime
            if age < self.cache_ttl_seconds:
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception as e:
                    logger.warning(f"Error reading cache {cache_file}: {e}")

        # Fetch from remote GitHub repo
        url = self.BASE_URL.format(year=year, topic=topic)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TechConferenceNotifier/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    raw_data = resp.read().decode("utf-8")
                    data = json.loads(raw_data)
                    with open(cache_file, "w", encoding="utf-8") as f:
                        f.write(raw_data)
                    return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump([], f)
                return []
        except Exception as e:
            logger.debug(f"Error fetching {url}: {e}")

        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def fetch(self, start_date: date, end_date: date, topics: List[str] | None = None) -> List[Conference]:
        years = range(start_date.year, end_date.year + 1)
        conferences: List[Conference] = []
        seen_ids = set()

        # Fetch key topics
        fetch_topics = ALL_CONFS_TECH_TOPICS

        for year in years:
            for topic in fetch_topics:
                items = self._get_cached_or_download(year, topic)
                if not items:
                    continue

                for item in items:
                    raw_start = item.get("startDate")
                    if not raw_start:
                        continue
                    try:
                        conf_start = datetime.strptime(raw_start, "%Y-%m-%d").date()
                    except ValueError:
                        continue

                    raw_end = item.get("endDate")
                    conf_end = None
                    if raw_end:
                        try:
                            conf_end = datetime.strptime(raw_end, "%Y-%m-%d").date()
                        except ValueError:
                            conf_end = conf_start

                    effective_end = conf_end or conf_start
                    if effective_end < start_date or conf_start > end_date:
                        continue

                    name = item.get("name", "Unnamed Conference").strip()
                    url = item.get("url", "").strip()

                    # Gatekeeper check
                    is_tech, reason = EventClassifier.is_tech_event(name, "")
                    if not is_tech:
                        continue

                    # Classify into 16 categories
                    primary_cat, sec_cats, conf_score = EventClassifier.classify(name, topic)
                    audiences = EventClassifier.detect_audiences(name)

                    cfp_deadline = None
                    raw_cfp = item.get("cfpEndDate")
                    if raw_cfp:
                        try:
                            cfp_deadline = datetime.strptime(raw_cfp, "%Y-%m-%d").date()
                        except ValueError:
                            pass

                    city = item.get("city") or "Not announced"
                    country = item.get("country") or "Not announced"
                    online = bool(item.get("online", False))
                    fmt = "virtual" if online else "in_person"
                    cfp_url = item.get("cfpUrl")

                    conf = Conference(
                        name=name,
                        category=primary_cat,
                        secondary_categories=sec_cats,
                        confidence_score=conf_score,
                        target_audiences=audiences,
                        source=self.name,
                        start_date=conf_start,
                        end_date=conf_end,
                        city=city,
                        country=country,
                        format=fmt,
                        url=url,
                        cfp_deadline=cfp_deadline,
                        cfp_url=cfp_url,
                        verification_status="verified",
                        sources=[{"source_name": "confs.tech", "url": url}],
                        metadata={
                            "twitter": item.get("twitter"),
                            "cocUrl": item.get("cocUrl")
                        }
                    )

                    if conf.id not in seen_ids:
                        seen_ids.add(conf.id)
                        conferences.append(conf)

        return conferences
