from __future__ import annotations

import json
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

import pytest

import tech_conf_notifier.api as api
from tech_conf_notifier.database import Database
from tech_conf_notifier.models import Conference, MANDATORY_CATEGORIES


@pytest.fixture
def api_test_client(isolated_db: Database, mock_manila_today: date):
    """Sets up Flask test client with an isolated in-memory/tmp database and seeded events."""
    api.app.config["TESTING"] = True
    api.db = isolated_db
    api.engine.db = isolated_db

    # Seed events
    c1 = Conference(
        name="Philippine Tech Expo 2026",
        category="Software Engineering",
        source="regional_ph",
        start_date=mock_manila_today + timedelta(days=10),
        end_date=mock_manila_today + timedelta(days=12),
        city="Taguig",
        country="Philippines",
        format="in_person",
        description="National software engineering expo.",
        url="https://philtechexpo.ph"
    )
    c2 = Conference(
        name="Global AI Summit 2026",
        category="Artificial Intelligence and Machine Learning",
        source="ccf-deadlines",
        start_date=mock_manila_today + timedelta(days=30),
        end_date=mock_manila_today + timedelta(days=32),
        city="Singapore",
        country="Singapore",
        format="virtual",
        description="International AI and deep learning symposium.",
        url="https://globalai.sg"
    )

    isolated_db.upsert_conference(c1)
    isolated_db.upsert_conference(c2)

    with api.app.test_client() as client:
        yield client, c1, c2


class TestApiEndpoints:
    """Test suite for Flask mobile REST API endpoints."""

    def test_get_events_endpoint(self, api_test_client):
        client, c1, c2 = api_test_client

        # 1. Base query
        res = client.get("/api/events")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "success"
        assert data["total"] == 2
        assert len(data["events"]) == 2

        # 2. Filter by category
        res_cat = client.get("/api/events?category=Software+Engineering")
        assert res_cat.status_code == 200
        data_cat = res_cat.get_json()
        assert data_cat["total"] == 1
        assert data_cat["events"][0]["id"] == c1.id

        # 3. Filter by format
        res_fmt = client.get("/api/events?format=virtual")
        assert res_fmt.status_code == 200
        data_fmt = res_fmt.get_json()
        assert data_fmt["total"] == 1
        assert data_fmt["events"][0]["id"] == c2.id

        # 4. Filter by Philippines
        res_ph = client.get("/api/events?country=philippines")
        assert res_ph.status_code == 200
        data_ph = res_ph.get_json()
        assert data_ph["total"] == 1
        assert data_ph["events"][0]["id"] == c1.id

        # 5. Search text
        res_search = client.get("/api/events?search=Singapore")
        assert res_search.status_code == 200
        data_search = res_search.get_json()
        assert data_search["total"] == 1
        assert data_search["events"][0]["id"] == c2.id

    def test_get_event_detail_endpoint(self, api_test_client):
        client, c1, _ = api_test_client

        # Existing event
        res = client.get(f"/api/events/{c1.id}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "success"
        assert data["event"]["id"] == c1.id
        assert data["event"]["name"] == c1.name

        # Non-existent event
        res_404 = client.get("/api/events/non_existent_id")
        assert res_404.status_code == 404
        assert res_404.get_json()["status"] == "error"

    def test_get_categories_endpoint(self, api_test_client):
        client, c1, c2 = api_test_client

        res = client.get("/api/categories")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "success"
        cats = data["categories"]
        assert len(cats) == 16

        cat_names = [c["name"] for c in cats]
        for mc in MANDATORY_CATEGORIES:
            assert mc in cat_names

        # Count check
        se_cat = next(c for c in cats if c["name"] == "Software Engineering")
        assert se_cat["count"] == 1
        ai_cat = next(c for c in cats if c["name"] == "Artificial Intelligence and Machine Learning")
        assert ai_cat["count"] == 1

    def test_bookmarks_workflow(self, api_test_client):
        client, c1, _ = api_test_client

        # Initially no bookmarks
        res_initial = client.get("/api/bookmarks")
        assert res_initial.status_code == 200
        assert res_initial.get_json()["total"] == 0

        # Toggle bookmark ON
        res_toggle_on = client.post(f"/api/bookmarks/{c1.id}")
        assert res_toggle_on.status_code == 200
        assert res_toggle_on.get_json()["is_bookmarked"] is True

        # Verify bookmark listed
        res_after = client.get("/api/bookmarks")
        assert res_after.status_code == 200
        data_after = res_after.get_json()
        assert data_after["total"] == 1
        assert data_after["events"][0]["id"] == c1.id
        assert data_after["events"][0]["is_bookmarked"] is True

        # Toggle bookmark OFF
        res_toggle_off = client.post(f"/api/bookmarks/{c1.id}")
        assert res_toggle_off.status_code == 200
        assert res_toggle_off.get_json()["is_bookmarked"] is False

        # Verify bookmark removed
        res_final = client.get("/api/bookmarks")
        assert res_final.status_code == 200
        assert res_final.get_json()["total"] == 0

    def test_calendar_ics_endpoint(self, api_test_client):
        client, c1, _ = api_test_client

        # Existing event
        res = client.get(f"/api/calendar/{c1.id}.ics")
        assert res.status_code == 200
        assert "text/calendar" in res.headers["Content-Type"]
        ics_text = res.data.decode("utf-8")
        assert "BEGIN:VCALENDAR" in ics_text
        assert "BEGIN:VEVENT" in ics_text
        assert f"UID:{c1.id}@techconfnotifier.org" in ics_text
        assert f"SUMMARY:{c1.name}" in ics_text
        assert "END:VEVENT" in ics_text
        assert "END:VCALENDAR" in ics_text

        # Non-existent event
        res_404 = client.get("/api/calendar/invalid_id.ics")
        assert res_404.status_code == 404

    def test_notifications_endpoint(self, api_test_client, isolated_db: Database):
        client, c1, _ = api_test_client
        isolated_db.record_notification(c1.id, "initial", "desktop", status="success")

        res = client.get("/api/notifications")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "success"
        assert len(data["notifications"]) >= 1
        assert data["notifications"][0]["event_id"] == c1.id
        assert data["notifications"][0]["trigger_type"] == "initial"

    def test_sync_endpoint(self, api_test_client):
        client, _, _ = api_test_client

        with patch.object(api.engine, "process_and_notify", return_value={"total_conferences": 10, "alerts_sent": 2, "dispatches": {}}):
            res = client.post("/api/sync")
            assert res.status_code == 200
            data = res.get_json()
            assert data["status"] == "success"
            assert "result" in data
            assert data["result"]["total_conferences"] == 10
