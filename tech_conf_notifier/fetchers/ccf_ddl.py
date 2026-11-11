from __future__ import annotations

import logging
import re
import time
from datetime import date, datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import urllib.request
import urllib.error
import yaml

from tech_conf_notifier.fetchers.base import BaseFetcher
from tech_conf_notifier.models import Conference
from tech_conf_notifier.classifier import EventClassifier

logger = logging.getLogger("tech_conf_notifier.fetchers.ccf_ddl")

CCF_CATEGORIES: Dict[str, Dict[str, str]] = {
    "AI": {
        "nips.yml": "NeurIPS (Neural Information Processing Systems)",
        "icml.yml": "ICML (International Conference on Machine Learning)",
        "cvpr.yml": "CVPR (IEEE Conference on Computer Vision and Pattern Recognition)",
        "iclr.yml": "ICLR (International Conference on Learning Representations)",
        "aaai.yml": "AAAI Conference on Artificial Intelligence",
        "acl.yml": "ACL (Association for Computational Linguistics)",
        "emnlp.yml": "EMNLP (Empirical Methods in Natural Language Processing)",
        "kdd.yml": "KDD (Knowledge Discovery and Data Mining)",
        "ijcai.yml": "IJCAI (International Joint Conference on Artificial Intelligence)"
    },
    "SC": {
        "sp.yml": "IEEE S&P (Symposium on Security and Privacy)",
        "ccs.yml": "ACM CCS (Conference on Computer and Communications Security)",
        "sec.yml": "USENIX Security Symposium",
        "ndss.yml": "NDSS (Network and Distributed System Security Symposium)",
        "crypto.yml": "CRYPTO (International Cryptology Conference)"
    },
    "SE": {
        "icse.yml": "ICSE (International Conference on Software Engineering)",
        "fse.yml": "FSE (ACM Joint European Software Engineering Conference)",
        "ase.yml": "ASE (Automated Software Engineering)",
        "issta.yml": "ISSTA (International Symposium on Software Testing and Analysis)"
    },
    "NW": {
        "sigcomm.yml": "ACM SIGCOMM (Special Interest Group on Data Communication)",
        "infocom.yml": "IEEE INFOCOM (International Conference on Computer Communications)",
        "nsdi.yml": "USENIX NSDI (Networked Systems Design and Implementation)",
        "mobicom.yml": "ACM MobiCom (Mobile Computing and Networking)"
    },
    "DS": {
        "osdi.yml": "USENIX OSDI (Operating Systems Design and Implementation)",
        "sosp.yml": "ACM SOSP (Symposium on Operating Systems Principles)",
        "eurosys.yml": "EuroSys (European Conference on Computer Systems)",
        "fast.yml": "USENIX FAST (File and Storage Technologies)"
    },
    "DB": {
        "sigmod.yml": "ACM SIGMOD (Management of Data)",
        "vldb.yml": "VLDB (Very Large Data Bases)",
        "icde.yml": "IEEE ICDE (International Conference on Data Engineering)"
    },
    "HI": {
        "chi.yml": "ACM CHI (Human Factors in Computing Systems)",
        "uist.yml": "ACM UIST (User Interface Software and Technology)"
    }
}


class CCFDeadlinesFetcher(BaseFetcher):
    """
    Fetches premier Computer Science academic and research conferences
    from the CCF-Deadlines open repository.
    """

    BASE_URL = "https://raw.githubusercontent.com/ccfddl/ccf-deadlines/main/conference/{sub}/{filename}"

    def __init__(self, cache_dir: str | Path = ".cache/ccfddl", cache_ttl_hours: int = 24):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl_seconds = cache_ttl_hours * 3600

    @property
    def name(self) -> str:
        return "ccf-deadlines"

    def _parse_conf_date(self, date_str: str) -> Tuple[Optional[date], Optional[date]]:
        if not date_str:
            return None, None
        s = date_str.strip()

        m1 = re.search(r'([A-Za-z]+)\s+(\d{1,2})\s*[-–]\s*(\d{1,2}),?\s+(\d{4})', s)
        if m1:
            mon, d1, d2, y = m1.groups()
            try:
                start = datetime.strptime(f"{mon} {d1} {y}", "%B %d %Y").date()
                end = datetime.strptime(f"{mon} {d2} {y}", "%B %d %Y").date()
                return start, end
            except ValueError:
                pass

        m2 = re.search(r'([A-Za-z]+)\s+(\d{1,2})\s*[-–]\s*([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})', s)
        if m2:
            mon1, d1, mon2, d2, y = m2.groups()
            try:
                start = datetime.strptime(f"{mon1} {d1} {y}", "%B %d %Y").date()
                end = datetime.strptime(f"{mon2} {d2} {y}", "%B %d %Y").date()
                return start, end
            except ValueError:
                pass

        m3 = re.search(r'([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})', s)
        if m3:
            mon, d, y = m3.groups()
            try:
                dt = datetime.strptime(f"{mon} {d} {y}", "%B %d %Y").date()
                return dt, dt
            except ValueError:
                pass

        return None, None

    def _get_cached_or_download(self, sub: str, filename: str) -> Optional[str]:
        cache_file = self.cache_dir / f"{sub}_{filename}"
        if cache_file.exists():
            age = time.time() - cache_file.stat().st_mtime
            if age < self.cache_ttl_seconds:
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        return f.read()
                except Exception:
                    pass

        url = self.BASE_URL.format(sub=sub, filename=filename)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TechConferenceNotifier/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    raw_text = resp.read().decode("utf-8")
                    with open(cache_file, "w", encoding="utf-8") as f:
                        f.write(raw_text)
                    return raw_text
        except Exception as e:
            logger.debug(f"Failed to fetch {url}: {e}")

        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass
        return None

    def fetch(self, start_date: date, end_date: date, topics: List[str] | None = None) -> List[Conference]:
        conferences: List[Conference] = []
        seen_ids = set()

        for sub, conf_dict in CCF_CATEGORIES.items():
            for filename, full_title in conf_dict.items():
                content = self._get_cached_or_download(sub, filename)
                if not content:
                    continue

                try:
                    docs = yaml.safe_load(content)
                    if not docs or not isinstance(docs, list):
                        continue
                    doc = docs[0]
                except Exception:
                    continue

                title = doc.get("title", filename.replace(".yml", "").upper())
                desc = doc.get("description", full_title)
                confs = doc.get("confs", [])

                for item in confs:
                    year = item.get("year")
                    date_str = item.get("date")
                    if not date_str:
                        continue

                    conf_start, conf_end = self._parse_conf_date(date_str)
                    if not conf_start:
                        continue

                    effective_end = conf_end or conf_start
                    if effective_end < start_date or conf_start > end_date:
                        continue

                    place = item.get("place", "Not announced")
                    link = item.get("link", "")
                    is_online = "virtual" in place.lower() or "online" in place.lower()
                    fmt = "virtual" if is_online else "in_person"

                    city, country = "Not announced", "Not announced"
                    if place and place != "Not announced":
                        parts = [p.strip() for p in place.split(",") if p.strip()]
                        if len(parts) >= 2:
                            city = parts[0]
                            country = parts[-1]
                        elif parts:
                            country = parts[0]

                    conf_name = f"{title} {year}"
                    primary_cat, sec_cats, conf_score = EventClassifier.classify(conf_name, desc)
                    audiences = ["Researchers", "Developers"]

                    cfp_deadline = None
                    timeline = item.get("timeline", [])
                    if timeline and isinstance(timeline, list):
                        for tl in timeline:
                            dline = tl.get("deadline")
                            if dline:
                                try:
                                    clean_dline = dline.split()[0]
                                    cfp_deadline = datetime.strptime(clean_dline, "%Y-%m-%d").date()
                                    break
                                except ValueError:
                                    pass

                    conf = Conference(
                        name=conf_name,
                        category=primary_cat,
                        secondary_categories=sec_cats,
                        confidence_score=conf_score,
                        target_audiences=audiences,
                        source=self.name,
                        start_date=conf_start,
                        end_date=conf_end,
                        city=city,
                        country=country,
                        location=place,
                        format=fmt,
                        event_type="conference",
                        organizer=title,
                        url=link,
                        description=desc,
                        cfp_deadline=cfp_deadline,
                        verification_status="verified",
                        sources=[{"source_name": "ccf-deadlines", "url": link}],
                        metadata={"rank": doc.get("rank", {}), "place": place}
                    )

                    if conf.id not in seen_ids:
                        seen_ids.add(conf.id)
                        conferences.append(conf)

        return conferences
