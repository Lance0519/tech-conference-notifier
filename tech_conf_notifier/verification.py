from __future__ import annotations

import logging
import re
import urllib.request
import urllib.error
import requests
import urllib3
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Tuple

from tech_conf_notifier.models import Conference

urllib3.disable_warnings()
logger = logging.getLogger("tech_conf_notifier.verification")


def jaro_winkler_similarity(s1: str, s2: str) -> float:
    """Computes Jaro-Winkler string similarity between two strings (0.0 to 1.0)."""
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0

    len1, len2 = len(s1), len(s2)
    max_dist = max(len1, len2) // 2 - 1
    if max_dist < 0:
        max_dist = 0

    s1_matches = [False] * len1
    s2_matches = [False] * len2
    matches = 0

    for i in range(len1):
        start = max(0, i - max_dist)
        end = min(i + max_dist + 1, len2)
        for j in range(start, end):
            if s2_matches[j]:
                continue
            if s1[i] == s2[j]:
                s1_matches[i] = True
                s2_matches[j] = True
                matches += 1
                break

    if matches == 0:
        return 0.0

    t = 0
    k = 0
    for i in range(len1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            t += 1
        k += 1

    transpositions = t // 2
    jaro = (matches / len1 + matches / len2 + (matches - transpositions) / matches) / 3.0

    # Winkler prefix bonus (up to 4 chars)
    prefix = 0
    for i in range(min(4, min(len1, len2))):
        if s1[i] == s2[i]:
            prefix += 1
        else:
            break

    return jaro + prefix * 0.1 * (1.0 - jaro)


def token_sort_similarity(s1: str, s2: str) -> float:
    """Computes token sort ratio using Jaro-Winkler after sorting word tokens."""
    tokens1 = " ".join(sorted(re.sub(r"[^\w\s]", "", s1.lower()).split()))
    tokens2 = " ".join(sorted(re.sub(r"[^\w\s]", "", s2.lower()).split()))
    return jaro_winkler_similarity(tokens1, tokens2)


class EventVerifier:
    """
    Validates link health, detects event status changes (cancellations/postponements),
    enforces sentinel values, and deduplicates multi-source listings.
    """

    @classmethod
    def sanitize_sentinels(cls, conf: Conference) -> Conference:
        """Enforces strict 'Not announced' / 'Not available' sentinel policies."""
        if not conf.organizer or conf.organizer.strip() in ("", "TBA", "Unknown", "N/A"):
            conf.organizer = "Not announced"
        if not conf.location or conf.location.strip() in ("", "TBA", "Unknown", "N/A"):
            conf.location = "Not announced"
        if not conf.city or conf.city.strip() in ("", "TBA", "Unknown", "N/A"):
            conf.city = "Not announced"
        if not conf.country or conf.country.strip() in ("", "TBA", "Unknown", "N/A"):
            conf.country = "Not announced"
        if not conf.description or conf.description.strip() in ("", "TBA", "Unknown", "N/A"):
            conf.description = "Not available"
        if not conf.fee_amount or conf.fee_amount.strip() in ("", "TBA", "Unknown", "N/A"):
            conf.fee_amount = "Not announced"
        return conf

    @classmethod
    def verify_url_health(cls, url: str, timeout: int = 5) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Probes a URL to verify it's reachable and not a dead link.
        Uses requests with modern browser User-Agent and automatic redirect following.
        Returns (is_healthy, final_url, status_code).
        """
        if not url or not url.startswith("http"):
            return False, None, None

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        try:
            r = requests.get(url, headers=headers, timeout=timeout, verify=False, allow_redirects=True)
            # 2xx and 3xx are completely healthy
            if 200 <= r.status_code < 400:
                return True, r.url, r.status_code
            # 401 or 403 are often Cloudflare / bot-protection shields on real official sites
            if r.status_code in (401, 403):
                return True, url, r.status_code
            return False, None, r.status_code
        except Exception:
            # Fallback to urllib if requests encounters connection adapter error
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return 200 <= resp.status < 400, resp.geturl(), resp.status
            except urllib.error.HTTPError as e:
                if e.code in (401, 403):
                    return True, url, e.code
                return False, None, e.code
            except Exception:
                return False, None, None

    @classmethod
    def detect_status_changes(cls, name: str, description: str, text_snippet: str = "") -> str:
        """Detects if an event is cancelled, postponed, or rescheduled."""
        corpus = f"{name} {description} {text_snippet}".lower()
        if any(w in corpus for w in ["cancelled", "canceled", "has been called off", "will not take place"]):
            return "cancelled"
        if any(w in corpus for w in ["postponed", "delayed until further notice", "to be rescheduled"]):
            return "postponed"
        if any(w in corpus for w in ["rescheduled", "new dates announced", "dates shifted"]):
            return "rescheduled"
        return "scheduled"

    @classmethod
    def are_duplicates(cls, c1: Conference, c2: Conference) -> bool:
        """
        Evaluates whether two conference listings refer to the exact same event.
        Requires:
        1. Start dates within +/- 3 days of each other
        2. Token similarity >= 0.88 or exact domain match
        """
        if not c1.start_date or not c2.start_date:
            return False

        # Date proximity check
        day_diff = abs((c1.start_date - c2.start_date).days)
        if day_diff > 3:
            return False

        # Exact canonical URL match
        if c1.url and c2.url:
            u1 = re.sub(r"^https?://(www\.)?", "", c1.url.lower().rstrip("/")).split("?")[0]
            u2 = re.sub(r"^https?://(www\.)?", "", c2.url.lower().rstrip("/")).split("?")[0]
            if u1 and u1 == u2:
                return True

        # Fuzzy token sort similarity
        sim = token_sort_similarity(c1.normalized_name, c2.normalized_name)
        if sim >= 0.88:
            return True

        return False

    @classmethod
    def merge_events(cls, primary: Conference, secondary: Conference) -> Conference:
        """Merges duplicate listings, preserving the most complete verified details."""
        # Preserve richer description
        if (not primary.description or primary.description == "Not available") and secondary.description != "Not available":
            primary.description = secondary.description

        # Preserve registration/CFP details
        if not primary.registration_url and secondary.registration_url:
            primary.registration_url = secondary.registration_url
        if not primary.cfp_deadline and secondary.cfp_deadline:
            primary.cfp_deadline = secondary.cfp_deadline
        if not primary.cfp_url and secondary.cfp_url:
            primary.cfp_url = secondary.cfp_url

        # Preserve organizer
        if (not primary.organizer or primary.organizer == "Not announced") and secondary.organizer != "Not announced":
            primary.organizer = secondary.organizer

        # Combine source provenance
        if secondary.source and secondary.source not in [s.get("source_name") for s in primary.sources]:
            primary.sources.append({
                "source_name": secondary.source,
                "url": secondary.url,
                "merged_at": datetime.now().isoformat()
            })

        return primary
