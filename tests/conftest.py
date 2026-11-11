from __future__ import annotations

import io
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

from tech_conf_notifier.database import Database
from tech_conf_notifier.models import Conference, MANILA_TZ


@pytest.fixture
def isolated_db(tmp_path: Path):
    """
    Creates an isolated SQLite database instance in a temporary directory
    with Write-Ahead Logging (WAL) enabled and scoped sessions.
    """
    db_file = tmp_path / "test_conferences.db"
    # Reset singleton instance
    Database._instance = None
    db = Database(db_path=db_file)
    Database._instance = db
    yield db
    Database._instance = None
    if hasattr(db, "engine"):
        db.engine.dispose()


@pytest.fixture
def mock_manila_today():
    """Returns today's date in Manila timezone."""
    return datetime.now(MANILA_TZ).date()


@pytest.fixture
def sample_conference_ph(mock_manila_today: date) -> Conference:
    """Fixture providing a realistic Philippine local tech conference."""
    return Conference(
        name="DEVCON Summit Philippines 2026",
        category="Software Engineering",
        source="regional_ph",
        start_date=mock_manila_today + timedelta(days=10),
        end_date=mock_manila_today + timedelta(days=11),
        city="Taguig, Metro Manila",
        country="Philippines",
        location="SMX Convention Center Aura, BGC",
        format="in_person",
        event_type="summit",
        organizer="DEVCON Philippines",
        url="https://devcon.ph/summit",
        description="The biggest developer conference in the Philippines bringing together 2,000+ tech leaders.",
        fee_type="paid",
        fee_amount="₱1,500 - ₱3,500",
        cfp_deadline=mock_manila_today + timedelta(days=3),
        cfp_url="https://devcon.ph/cfp",
        target_audiences=["Developers", "Students", "IT Executives"],
        verification_status="verified",
        confidence_score=0.95
    )


@pytest.fixture
def sample_conference_intl(mock_manila_today: date) -> Conference:
    """Fixture providing a realistic international virtual AI conference."""
    return Conference(
        name="NeurIPS 2026",
        category="Artificial Intelligence and Machine Learning",
        source="ccf-deadlines",
        start_date=mock_manila_today + timedelta(days=45),
        end_date=mock_manila_today + timedelta(days=50),
        city="Vancouver",
        country="Canada",
        location="Vancouver Convention Centre",
        format="virtual",
        event_type="conference",
        organizer="Neural Information Processing Systems Foundation",
        url="https://nips.cc",
        description="Annual conference on Neural Information Processing Systems covering deep learning and theoretical machine learning.",
        fee_type="paid",
        fee_amount="$450 - $1,100 USD",
        cfp_deadline=mock_manila_today + timedelta(days=14),
        cfp_url="https://nips.cc/call-for-papers",
        target_audiences=["Researchers", "Developers"],
        verification_status="verified",
        confidence_score=0.98
    )


@pytest.fixture
def sample_conferences(mock_manila_today: date) -> List[Conference]:
    """Fixture providing a diverse list of conferences across categories, formats, and regions."""
    return [
        Conference(
            name="ROOTCON 20 2026",
            category="Cybersecurity",
            source="regional_ph",
            start_date=mock_manila_today + timedelta(days=15),
            end_date=mock_manila_today + timedelta(days=16),
            city="Tagaytay City",
            country="Philippines",
            format="hybrid",
            organizer="ROOTCON Information Security",
            url="https://www.rootcon.org",
            description="Premier information security conference in the Philippines.",
            fee_type="paid",
            fee_amount="₱4,500",
            target_audiences=["Developers", "Researchers"]
        ),
        Conference(
            name="Cloud Native Manila Summit 2026",
            category="Cloud Computing and DevOps",
            source="custom",
            start_date=mock_manila_today + timedelta(days=5),
            end_date=mock_manila_today + timedelta(days=5),
            city="Makati City",
            country="Philippines",
            format="in_person",
            organizer="Cloud Native Philippines",
            url="https://cloudnativemanila.org",
            description="Kubernetes, microservices, and observability summit.",
            fee_type="free",
            fee_amount="Free admission",
            target_audiences=["Developers", "IT Executives"]
        ),
        Conference(
            name="Global Web & Mobile Expo 2026",
            category="Web and Mobile Development",
            source="confs.tech",
            start_date=mock_manila_today + timedelta(days=25),
            end_date=mock_manila_today + timedelta(days=26),
            city="Tokyo",
            country="Japan",
            format="virtual",
            organizer="WebDev Global",
            url="https://webmobileexpo.org",
            description="Frontend frameworks, React, Flutter, and TypeScript advances.",
            fee_type="paid",
            fee_amount="$150",
            target_audiences=["Developers"]
        ),
        Conference(
            name="International Symposium on Computer Architecture 2026",
            category="Computer Engineering",
            source="ccf-deadlines",
            start_date=mock_manila_today + timedelta(days=70),
            end_date=mock_manila_today + timedelta(days=73),
            city="Seoul",
            country="South Korea",
            format="in_person",
            organizer="IEEE / ACM",
            url="https://isca2026.org",
            description="Premier forum for computer architecture research and microprocessor design.",
            fee_type="paid",
            fee_amount="$600",
            target_audiences=["Researchers"]
        ),
    ]


@pytest.fixture
def mock_http_response():
    """Factory fixture to create mock HTTP responses for urllib.request.urlopen."""
    def _create(status: int = 200, body: str | bytes = "", url: str = "https://example.com"):
        mock_resp = MagicMock()
        mock_resp.status = status
        mock_resp.code = status
        mock_resp.geturl.return_value = url
        if isinstance(body, str):
            encoded = body.encode("utf-8")
        else:
            encoded = body
        mock_resp.read.return_value = encoded
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = False
        return mock_resp
    return _create
