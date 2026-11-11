from __future__ import annotations

from datetime import date, datetime, timedelta
import pytest

from tech_conf_notifier.models import (
    Conference,
    normalize_text_for_id,
    MANDATORY_CATEGORIES,
    TARGET_AUDIENCE_PERSONAS,
    MANILA_TZ
)


class TestConferenceModel:
    """Test suite for Conference dataclass, sentinels, properties, and serialization."""

    def test_default_initialization_and_sentinels(self, mock_manila_today: date):
        conf = Conference(name="DevFest 2026")
        assert conf.name == "DevFest 2026"
        assert conf.category == "Information Technology"
        assert conf.source == "unknown"
        assert conf.start_date == date.today()
        assert conf.description == "Not available"
        assert conf.organizer == "Not announced"
        assert conf.city == "Not announced"
        assert conf.country == "Not announced"
        assert conf.location == "Not announced"
        assert conf.fee_amount == "Not announced"
        assert conf.fee_type == "unknown"
        assert conf.status == "scheduled"
        assert conf.verification_status == "unverified"
        assert conf.confidence_score == 0.5
        assert conf.geographic_tier == "international"
        assert conf.format == "in_person"
        assert conf.target_audiences == ["Developers"]
        assert conf.id != ""
        assert len(conf.id) == 16

    def test_normalize_text_for_id(self):
        text = "PyCon Philippines 2026 -- Special Edition!"
        norm = normalize_text_for_id(text)
        assert "2026" not in norm
        assert "--" not in norm
        assert "!" not in norm
        assert norm == "pycon philippines special edition"

    def test_deterministic_cluster_id(self, mock_manila_today: date):
        c1 = Conference(
            name="PyCon PH 2026",
            start_date=date(2026, 2, 20),
            url="https://pycon.python.ph/2026/?ref=home"
        )
        c2 = Conference(
            name="PyCon PH 2026",
            start_date=date(2026, 2, 20),
            url="http://pycon.python.ph/2026#agenda"
        )
        c3 = Conference(
            name="PyCon PH 2027",
            start_date=date(2027, 2, 20),
            url="https://pycon.python.ph/2027/"
        )
        # c1 and c2 have the same normalized name, same start date, and same base URL (ignoring http/https and query/hash)
        assert c1.id == c2.id
        assert c1.id != c3.id

    def test_geographic_tier_assignment(self):
        # Explicit country
        c_ph = Conference(name="Test Conf", country="Philippines")
        assert c_ph.geographic_tier == "local_ph"
        assert c_ph.is_philippines is True

        # Philippine city detection
        c_cebu = Conference(name="Test Conf", city="Cebu City")
        assert c_cebu.geographic_tier == "local_ph"
        assert c_cebu.country == "Philippines"
        assert c_cebu.iso_country == "PH"

        # ASEAN detection
        c_sg = Conference(name="Test SG", country="Singapore")
        assert c_sg.geographic_tier == "sea_asean"
        assert c_sg.is_philippines is False

        # International default
        c_us = Conference(name="Test US", country="United States")
        assert c_us.geographic_tier == "international"
        assert c_us.is_philippines is False

    def test_days_until_property(self, mock_manila_today: date):
        conf_future = Conference(name="Future Conf", start_date=mock_manila_today + timedelta(days=10))
        assert conf_future.days_until == 10

        conf_today = Conference(name="Today Conf", start_date=mock_manila_today)
        assert conf_today.days_until == 0

        conf_past = Conference(name="Past Conf", start_date=mock_manila_today - timedelta(days=5))
        assert conf_past.days_until == -5

    def test_status_label_progression(self, mock_manila_today: date):
        # Override statuses
        c_canc = Conference(name="C1", status="cancelled", start_date=mock_manila_today + timedelta(days=5))
        assert c_canc.status_label == "CANCELLED"

        c_post = Conference(name="C2", status="postponed", start_date=mock_manila_today + timedelta(days=5))
        assert c_post.status_label == "POSTPONED"

        c_resc = Conference(name="C3", status="rescheduled", start_date=mock_manila_today + timedelta(days=5))
        assert c_resc.status_label == "RESCHEDULED"

        # Days milestone labels
        c_today = Conference(name="Today", start_date=mock_manila_today)
        assert c_today.status_label == "Starts TODAY!"

        c_tom = Conference(name="Tomorrow", start_date=mock_manila_today + timedelta(days=1))
        assert c_tom.status_label == "Starts TOMORROW!"

        c_week = Conference(name="This Week", start_date=mock_manila_today + timedelta(days=5))
        assert c_week.status_label == "Starts in 5 days (This Week)"

        c_next_week = Conference(name="Next Week", start_date=mock_manila_today + timedelta(days=12))
        assert c_next_week.status_label == "Starts in 12 days (Next Week)"

        c_month = Conference(name="Next Month", start_date=mock_manila_today + timedelta(days=25))
        assert c_month.status_label == "Starts in 25 days (~1 month)"

        c_far = Conference(name="Far Future", start_date=mock_manila_today + timedelta(days=60))
        assert c_far.status_label == "Starts in 60 days"

        # Ongoing / Happening Now
        c_ongoing = Conference(
            name="Ongoing Conf",
            start_date=mock_manila_today - timedelta(days=1),
            end_date=mock_manila_today + timedelta(days=2)
        )
        assert c_ongoing.status_label == "Happening Now (Ongoing)"

        # Passed
        c_passed_1 = Conference(
            name="Passed 1",
            start_date=mock_manila_today - timedelta(days=1),
            end_date=mock_manila_today - timedelta(days=1)
        )
        assert c_passed_1.status_label == "Passed 1 day ago"

        c_passed_5 = Conference(
            name="Passed 5",
            start_date=mock_manila_today - timedelta(days=5),
            end_date=mock_manila_today - timedelta(days=5)
        )
        assert c_passed_5.status_label == "Passed 5 days ago"

    def test_location_str_formatting(self):
        # In person with city and country
        c1 = Conference(name="C1", format="in_person", city="Makati City", country="Philippines")
        assert c1.location_str == "Makati City, Philippines"

        # In person with neither
        c2 = Conference(name="C2", format="in_person")
        assert c2.location_str == "Location TBA"

        # Virtual
        c3 = Conference(name="C3", format="virtual", city="New York", country="USA")
        assert c3.location_str == "Online / Virtual"

        # Hybrid with city and country
        c4 = Conference(name="C4", format="hybrid", city="Tagaytay", country="Philippines")
        assert c4.location_str == "Hybrid (Tagaytay, Philippines + Online)"

        # Hybrid without city/country
        c5 = Conference(name="C5", format="hybrid")
        assert c5.location_str == "Hybrid (Location TBA + Online)"

    def test_formatted_date_range(self):
        # Single day
        c1 = Conference(name="C1", start_date=date(2026, 11, 20), end_date=date(2026, 11, 20))
        assert c1.formatted_date_range == "Nov 20, 2026"

        # Same month multi-day
        c2 = Conference(name="C2", start_date=date(2026, 11, 20), end_date=date(2026, 11, 22))
        assert c2.formatted_date_range == "Nov 20-22, 2026"

        # Same year different month
        c3 = Conference(name="C3", start_date=date(2026, 11, 28), end_date=date(2026, 12, 2))
        assert c3.formatted_date_range == "Nov 28 - Dec 02, 2026"

        # Across years
        c4 = Conference(name="C4", start_date=date(2026, 12, 30), end_date=date(2027, 1, 3))
        assert c4.formatted_date_range == "Dec 30, 2026 - Jan 03, 2027"

    def test_helper_properties(self, mock_manila_today: date):
        # is_online
        assert Conference(name="A", format="virtual").is_online is True
        assert Conference(name="B", format="hybrid").is_online is True
        assert Conference(name="C", format="in_person").is_online is False

        # is_free
        assert Conference(name="F1", fee_type="free").is_free is True
        assert Conference(name="F2", fee_amount="Free (Registration required)").is_free is True
        assert Conference(name="F3", fee_type="paid", fee_amount="₱2,500").is_free is False

        # has_cfp_open
        assert Conference(name="CFP1", cfp_deadline=mock_manila_today + timedelta(days=5)).has_cfp_open is True
        assert Conference(name="CFP2", cfp_deadline=mock_manila_today - timedelta(days=1)).has_cfp_open is False
        assert Conference(name="CFP3", cfp_deadline=None).has_cfp_open is False

    def test_to_dict_and_from_dict_roundtrip(self, sample_conference_ph: Conference):
        conf_dict = sample_conference_ph.to_dict()
        assert isinstance(conf_dict, dict)
        assert conf_dict["name"] == sample_conference_ph.name
        assert conf_dict["start_date"] == sample_conference_ph.start_date.isoformat()
        assert conf_dict["location_str"] == sample_conference_ph.location_str
        assert conf_dict["is_philippines"] is True
        assert "has_cfp_open" in conf_dict

        reconstructed = Conference.from_dict(conf_dict)
        assert reconstructed.name == sample_conference_ph.name
        assert reconstructed.id == sample_conference_ph.id
        assert reconstructed.category == sample_conference_ph.category
        assert reconstructed.start_date == sample_conference_ph.start_date
        assert reconstructed.end_date == sample_conference_ph.end_date
        assert reconstructed.url == sample_conference_ph.url
        assert reconstructed.city == sample_conference_ph.city
        assert reconstructed.country == sample_conference_ph.country
        assert reconstructed.format == sample_conference_ph.format

    def test_from_dict_backwards_compatibility(self):
        legacy_data = {
            "name": "Legacy Tech Meetup",
            "topic": "Cybersecurity",
            "start_date": "2026-12-10",
            "is_online": True,
            "url": "https://example.com/legacy"
        }
        conf = Conference.from_dict(legacy_data)
        assert conf.name == "Legacy Tech Meetup"
        assert conf.category == "Cybersecurity"
        assert conf.format == "virtual"
        assert conf.start_date == date(2026, 12, 10)
