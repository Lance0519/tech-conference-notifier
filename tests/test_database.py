from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import pytest
from sqlalchemy import text

from tech_conf_notifier.database import (
    Database,
    EventModel,
    BookmarkModel,
    NotificationHistoryModel
)
from tech_conf_notifier.models import Conference


class TestDatabase:
    """Test suite for SQLite WAL mode, schema, upserts, multi-parameter querying, bookmarks, and notification tracking."""

    def test_sqlite_pragmas_and_wal_mode(self, isolated_db: Database):
        """Verifies Write-Ahead Logging (WAL) mode and foreign keys are active."""
        with isolated_db.session_scope() as session:
            journal_mode = session.execute(text("PRAGMA journal_mode;")).scalar()
            assert str(journal_mode).lower() == "wal"

            foreign_keys = session.execute(text("PRAGMA foreign_keys;")).scalar()
            assert foreign_keys == 1

            busy_timeout = session.execute(text("PRAGMA busy_timeout;")).scalar()
            assert busy_timeout == 30000

    def test_upsert_insert_and_update(self, isolated_db: Database, mock_manila_today: date):
        conf = Conference(
            name="Manila AI Summit 2026",
            category="Artificial Intelligence and Machine Learning",
            start_date=mock_manila_today + timedelta(days=20),
            end_date=mock_manila_today + timedelta(days=21),
            city="Taguig",
            country="Philippines",
            format="in_person",
            description="Initial event overview.",
            url="https://manila-ai.org"
        )
        conf_id = conf.id

        # 1. Insert
        isolated_db.upsert_conference(conf)
        events = isolated_db.get_upcoming_events(days_lookahead=60)
        assert len(events) == 1
        assert events[0].id == conf_id
        assert events[0].description == "Initial event overview."

        # 2. Update with richer description and changed format
        conf.description = "Updated comprehensive agenda with generative AI tracks."
        conf.format = "hybrid"
        isolated_db.upsert_conference(conf)

        events_updated = isolated_db.get_upcoming_events(days_lookahead=60)
        assert len(events_updated) == 1
        assert events_updated[0].description == "Updated comprehensive agenda with generative AI tracks."
        assert events_updated[0].format == "hybrid"

    def test_query_filters(self, isolated_db: Database, mock_manila_today: date):
        c_ph_cyber = Conference(
            name="ROOTCON PH",
            category="Cybersecurity",
            start_date=mock_manila_today + timedelta(days=10),
            country="Philippines",
            city="Tagaytay",
            format="in_person",
            url="https://rootcon.org"
        )
        c_us_cloud = Conference(
            name="Cloud Con US",
            category="Cloud Computing and DevOps",
            start_date=mock_manila_today + timedelta(days=15),
            country="USA",
            city="Seattle",
            format="virtual",
            url="https://cloudcon.us"
        )
        c_sg_web = Conference(
            name="JSConf Singapore",
            category="Web and Mobile Development",
            start_date=mock_manila_today + timedelta(days=40),
            country="Singapore",
            city="Singapore",
            format="hybrid",
            url="https://jsconf.asia"
        )
        c_cancelled = Conference(
            name="Cancelled Tech Summit",
            category="Cybersecurity",
            start_date=mock_manila_today + timedelta(days=5),
            status="cancelled",
            url="https://cancelled.org"
        )

        for c in [c_ph_cyber, c_us_cloud, c_sg_web, c_cancelled]:
            isolated_db.upsert_conference(c)

        # Base upcoming query (should exclude cancelled event)
        all_upcoming = isolated_db.get_upcoming_events(days_lookahead=60)
        assert len(all_upcoming) == 3
        assert not any(e.name == "Cancelled Tech Summit" for e in all_upcoming)

        # Filter by category
        cyber_events = isolated_db.get_upcoming_events(category="Cybersecurity")
        assert len(cyber_events) == 1
        assert cyber_events[0].name == "ROOTCON PH"

        # Filter by format
        virtual_events = isolated_db.get_upcoming_events(format_filter="virtual")
        assert len(virtual_events) == 1
        assert virtual_events[0].name == "Cloud Con US"

        # Filter by Philippines
        ph_events = isolated_db.get_upcoming_events(country="Philippines")
        assert len(ph_events) == 1
        assert ph_events[0].name == "ROOTCON PH"

        # Filter by other country
        sg_events = isolated_db.get_upcoming_events(country="Singapore")
        assert len(sg_events) == 1
        assert sg_events[0].name == "JSConf Singapore"

        # Filter by search text
        searched = isolated_db.get_upcoming_events(search_query="Seattle")
        assert len(searched) == 1
        assert searched[0].name == "Cloud Con US"

    def test_bookmark_lifecycle(self, isolated_db: Database, mock_manila_today: date):
        conf = Conference(
            name="Bookmarked Conference",
            category="Software Engineering",
            start_date=mock_manila_today + timedelta(days=20),
            url="https://example.com/bm"
        )
        isolated_db.upsert_conference(conf)

        # Initially not bookmarked
        initial_bm = isolated_db.get_bookmarked_event_ids()
        assert conf.id not in initial_bm

        # Toggle ON
        saved = isolated_db.toggle_bookmark(conf.id)
        assert saved is True
        assert conf.id in isolated_db.get_bookmarked_event_ids()

        # Toggle OFF
        removed = isolated_db.toggle_bookmark(conf.id)
        assert removed is False
        assert conf.id not in isolated_db.get_bookmarked_event_ids()

    def test_notification_history_tracking(self, isolated_db: Database, mock_manila_today: date):
        conf = Conference(
            name="Notified Conference",
            category="Data Science and Analytics",
            start_date=mock_manila_today + timedelta(days=7),
            url="https://example.com/notif"
        )
        isolated_db.upsert_conference(conf)

        # Check before recording
        assert isolated_db.is_notified(conf.id, "initial", "desktop") is False

        # Record notification
        isolated_db.record_notification(conf.id, "initial", "desktop", status="success")
        assert isolated_db.is_notified(conf.id, "initial", "desktop") is True

        # Different trigger or channel remains False
        assert isolated_db.is_notified(conf.id, "reminder_7d", "desktop") is False
        assert isolated_db.is_notified(conf.id, "initial", "discord") is False
