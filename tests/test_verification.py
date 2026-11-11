from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch, MagicMock
import urllib.error

import pytest

from tech_conf_notifier.models import Conference
from tech_conf_notifier.verification import (
    jaro_winkler_similarity,
    token_sort_similarity,
    EventVerifier
)


class TestEventVerification:
    """Test suite for string similarity, deduplication, merging, URL health, and status changes."""

    def test_jaro_winkler_similarity_properties(self):
        # Identical
        assert jaro_winkler_similarity("DevFest", "DevFest") == 1.0
        # Empty
        assert jaro_winkler_similarity("", "") == 1.0
        assert jaro_winkler_similarity("DevFest", "") == 0.0
        assert jaro_winkler_similarity("", "DevFest") == 0.0
        # Similar with prefix bonus
        sim = jaro_winkler_similarity("PythonConf", "PythonSummit")
        assert 0.70 < sim < 1.0

    def test_token_sort_similarity(self):
        # Order independent
        s1 = "DevOps World 2026 Summit"
        s2 = "Summit DevOps 2026 World"
        assert token_sort_similarity(s1, s2) == 1.0

        # Punctuation stripped
        s3 = "DevOps, World: 2026 (Summit)!"
        assert token_sort_similarity(s1, s3) == 1.0

    def test_are_duplicates_by_similarity_and_date(self, mock_manila_today: date):
        c1 = Conference(
            name="PyCon Philippines 2026",
            start_date=mock_manila_today + timedelta(days=20),
            url="https://pycon.python.ph"
        )
        c2 = Conference(
            name="PyCon PH 2026 Manila",
            start_date=mock_manila_today + timedelta(days=21),  # Within 3 days
            url="https://pycon.ph"
        )
        c3 = Conference(
            name="PyCon Philippines 2026",
            start_date=mock_manila_today + timedelta(days=30),  # > 3 days apart
            url="https://pycon.python.ph"
        )
        c4 = Conference(
            name="Different Cyber Security Summit",
            start_date=mock_manila_today + timedelta(days=20),
            url="https://cybersummit.com"
        )

        assert EventVerifier.are_duplicates(c1, c1) is True
        assert EventVerifier.are_duplicates(c1, c3) is False  # Date too far
        assert EventVerifier.are_duplicates(c1, c4) is False  # Different event

    def test_are_duplicates_by_canonical_url(self, mock_manila_today: date):
        # Slight name variation but identical canonical URL
        c1 = Conference(
            name="AWS Community Day Philippines",
            start_date=mock_manila_today + timedelta(days=10),
            url="https://awsug.ph/community-day?ref=feed"
        )
        c2 = Conference(
            name="AWS Community Day PH",
            start_date=mock_manila_today + timedelta(days=10),
            url="http://www.awsug.ph/community-day#schedule"
        )
        assert EventVerifier.are_duplicates(c1, c2) is True

    def test_event_merging(self, mock_manila_today: date):
        primary = Conference(
            name="SOFTCON 2026",
            category="Software Engineering",
            source="regional_ph",
            start_date=mock_manila_today + timedelta(days=30),
            description="Not available",
            organizer="Not announced",
            url="https://softcon.ph"
        )
        secondary = Conference(
            name="PSIA SOFTCON 2026",
            category="Software Engineering",
            source="confs.tech",
            start_date=mock_manila_today + timedelta(days=30),
            description="Premier software convention showcasing modern IT.",
            organizer="PSIA",
            registration_url="https://softcon.ph/tickets",
            cfp_deadline=mock_manila_today + timedelta(days=10),
            cfp_url="https://softcon.ph/cfp",
            url="https://softcon.ph"
        )

        merged = EventVerifier.merge_events(primary, secondary)
        assert merged.description == "Premier software convention showcasing modern IT."
        assert merged.organizer == "PSIA"
        assert merged.registration_url == "https://softcon.ph/tickets"
        assert merged.cfp_deadline == mock_manila_today + timedelta(days=10)
        assert merged.cfp_url == "https://softcon.ph/cfp"
        assert any(s["source_name"] == "confs.tech" for s in merged.sources)

    def test_sanitize_sentinels(self):
        conf = Conference(
            name="Test Conf",
            organizer="TBA",
            location="Unknown",
            city="N/A",
            country="",
            description="   ",
            fee_amount="TBA"
        )
        sanitized = EventVerifier.sanitize_sentinels(conf)
        assert sanitized.organizer == "Not announced"
        assert sanitized.location == "Not announced"
        assert sanitized.city == "Not announced"
        assert sanitized.country == "Not announced"
        assert sanitized.description == "Not available"
        assert sanitized.fee_amount == "Not announced"

    def test_detect_status_changes(self):
        # Cancelled
        assert EventVerifier.detect_status_changes("Tech Conf", "This event has been cancelled due to weather.") == "cancelled"
        assert EventVerifier.detect_status_changes("Tech Conf", "The summit will not take place.") == "cancelled"

        # Postponed
        assert EventVerifier.detect_status_changes("Tech Conf", "The event is postponed until further notice.") == "postponed"

        # Rescheduled
        assert EventVerifier.detect_status_changes("Tech Conf", "Conference rescheduled to new dates announced.") == "rescheduled"

        # Scheduled (normal)
        assert EventVerifier.detect_status_changes("Tech Conf", "Join us for an exciting 2-day developer summit.") == "scheduled"

    @patch("requests.get")
    def test_verify_url_health_success(self, mock_requests_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = "https://example.com/conf"
        mock_requests_get.return_value = mock_resp
        healthy, final_url, status = EventVerifier.verify_url_health("https://example.com/conf")
        assert healthy is True
        assert final_url == "https://example.com/conf"
        assert status == 200

    @patch("requests.get")
    def test_verify_url_health_cloudflare_shield(self, mock_requests_get):
        # 403 should be treated as live/bot-shielded
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.url = "https://example.com"
        mock_requests_get.return_value = mock_resp
        healthy, final_url, status = EventVerifier.verify_url_health("https://example.com")
        assert healthy is True
        assert status == 403

    @patch("requests.get")
    def test_verify_url_health_dead_link_404(self, mock_requests_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.url = "https://example.com/dead"
        mock_requests_get.return_value = mock_resp
        healthy, final_url, status = EventVerifier.verify_url_health("https://example.com/dead")
        assert healthy is False
        assert status == 404

    def test_verify_url_health_invalid_url(self):
        healthy, final_url, status = EventVerifier.verify_url_health("not-a-valid-url")
        assert healthy is False
        assert final_url is None
        assert status is None
