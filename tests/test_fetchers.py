from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from tech_conf_notifier.fetchers.confs_tech import ConfsTechFetcher
from tech_conf_notifier.fetchers.ccf_ddl import CCFDeadlinesFetcher
from tech_conf_notifier.fetchers.regional_ph import RegionalPHFetcher
from tech_conf_notifier.fetchers.custom import CustomJsonFetcher


class TestFetchers:
    """Test suite for all conference fetchers: confs.tech, ccf-deadlines, regional_ph, and custom JSON."""

    def test_regional_ph_fetcher(self, mock_manila_today: date):
        fetcher = RegionalPHFetcher()
        assert fetcher.name == "regional_ph"

        # Fetch with broad window covering the seeds
        confs = fetcher.fetch(start_date=date(2026, 1, 1), end_date=date(2027, 12, 31))
        assert len(confs) >= 5

        names = [c.name for c in confs]
        assert any("DEVCON Summit" in n for n in names)
        assert any("ROOTCON" in n for n in names)
        assert any("SOFTCON" in n for n in names)

        # Check Philippine geographic tier enforcement
        devcon = next(c for c in confs if "DEVCON" in c.name)
        assert devcon.geographic_tier == "local_ph"
        assert devcon.country == "Philippines"
        assert devcon.verification_status == "verified"
        assert devcon.confidence_score >= 0.90

    def test_regional_ph_date_filtering(self):
        fetcher = RegionalPHFetcher()
        # Narrow window where no seeds exist
        confs = fetcher.fetch(start_date=date(2030, 1, 1), end_date=date(2030, 1, 5))
        assert len(confs) == 0

    def test_custom_json_fetcher_valid_file(self, tmp_path: Path):
        json_file = tmp_path / "custom.json"
        data = [
            {
                "name": "Manila Tech Week 2026",
                "topic": "Software Engineering",
                "startDate": "2026-11-15",
                "endDate": "2026-11-17",
                "city": "Manila",
                "country": "Philippines",
                "online": False,
                "url": "https://manilatechweek.ph",
                "description": "Annual gathering of Philippine software innovators.",
                "fee_type": "free",
                "fee_amount": "Free admission"
            }
        ]
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        fetcher = CustomJsonFetcher(json_path=json_file)
        assert fetcher.name == "custom"

        confs = fetcher.fetch(start_date=date(2026, 11, 1), end_date=date(2026, 11, 30))
        assert len(confs) == 1
        conf = confs[0]
        assert conf.name == "Manila Tech Week 2026"
        assert conf.category == "Software Engineering"
        assert conf.format == "in_person"
        assert conf.is_free is True
        assert conf.city == "Manila"
        assert conf.country == "Philippines"

    def test_custom_json_fetcher_missing_or_corrupt_file(self, tmp_path: Path):
        # Missing file
        missing_fetcher = CustomJsonFetcher(json_path=tmp_path / "non_existent.json")
        assert missing_fetcher.fetch(date(2026, 1, 1), date(2026, 12, 31)) == []

        # Corrupt JSON file
        corrupt_file = tmp_path / "bad.json"
        with open(corrupt_file, "w", encoding="utf-8") as f:
            f.write("{invalid_json:")
        corrupt_fetcher = CustomJsonFetcher(json_path=corrupt_file)
        assert corrupt_fetcher.fetch(date(2026, 1, 1), date(2026, 12, 31)) == []

    @patch("urllib.request.urlopen")
    def test_confs_tech_fetcher_download_and_cache(self, mock_urlopen, tmp_path: Path, mock_http_response):
        cache_dir = tmp_path / "confs_tech_cache"
        fetcher = ConfsTechFetcher(cache_dir=cache_dir, cache_ttl_hours=12)
        assert fetcher.name == "confs.tech"

        sample_confs_data = [
            {
                "name": "PyCascades 2026",
                "url": "https://pycascades.com",
                "startDate": "2026-04-10",
                "endDate": "2026-04-12",
                "city": "Seattle",
                "country": "USA",
                "online": False,
                "cfpUrl": "https://pycascades.com/cfp",
                "cfpEndDate": "2026-02-01"
            },
            {
                # Should be filtered out by non-tech gatekeeper
                "name": "National Dental Surgery Expo 2026",
                "url": "https://dental.com",
                "startDate": "2026-04-10",
                "endDate": "2026-04-12"
            }
        ]

        mock_urlopen.return_value = mock_http_response(status=200, body=json.dumps(sample_confs_data))

        # Test single topic download & cache
        results = fetcher._get_cached_or_download(year=2026, topic="python")
        assert results is not None
        assert len(results) == 2

        # Verify cache file written
        cached_file = cache_dir / "2026_python.json"
        assert cached_file.exists()

        # Subsequent call should read from cache (no extra urlopen call)
        mock_urlopen.reset_mock()
        cached_results = fetcher._get_cached_or_download(year=2026, topic="python")
        assert cached_results == results
        mock_urlopen.assert_not_called()

        # Test fetch execution with gatekeeper
        with patch.object(fetcher, "_get_cached_or_download", return_value=sample_confs_data):
            confs = fetcher.fetch(start_date=date(2026, 4, 1), end_date=date(2026, 4, 30))
            assert len(confs) == 1
            assert confs[0].name == "PyCascades 2026"
            assert confs[0].verification_status == "verified"
            assert confs[0].cfp_url == "https://pycascades.com/cfp"

    def test_ccf_deadlines_date_parser(self):
        fetcher = CCFDeadlinesFetcher()
        assert fetcher.name == "ccf-deadlines"

        # Case 1: Same month range "September 15 - 19, 2026"
        s1, e1 = fetcher._parse_conf_date("September 15 - 19, 2026")
        assert s1 == date(2026, 9, 15)
        assert e1 == date(2026, 9, 19)

        # Case 2: Cross month range "October 28 - November 02, 2026"
        s2, e2 = fetcher._parse_conf_date("October 28 - November 02, 2026")
        assert s2 == date(2026, 10, 28)
        assert e2 == date(2026, 11, 2)

        # Case 3: Single day "May 12, 2026"
        s3, e3 = fetcher._parse_conf_date("May 12, 2026")
        assert s3 == date(2026, 5, 12)
        assert e3 == date(2026, 5, 12)

        # Case 4: Invalid string
        s4, e4 = fetcher._parse_conf_date("TBD 2026")
        assert s4 is None
        assert e4 is None

    def test_ccf_deadlines_fetch_parsing(self, tmp_path: Path):
        cache_dir = tmp_path / "ccf_cache"
        fetcher = CCFDeadlinesFetcher(cache_dir=cache_dir)

        yaml_content = """
- title: NEURIPS
  description: Conference on Neural Information Processing Systems
  sub: AI
  rank:
    ccf: A
  confs:
    - year: 2026
      id: neurips26
      link: https://neurips.cc/2026
      timeline:
        - deadline: '2026-05-22 23:59:59'
          comment: Abstract Deadline
      date: December 06 - 12, 2026
      place: Vancouver, Canada
"""
        with patch.object(fetcher, "_get_cached_or_download", return_value=yaml_content):
            confs = fetcher.fetch(start_date=date(2026, 12, 1), end_date=date(2026, 12, 31))
            assert len(confs) >= 1
            conf = confs[0]
            assert "NEURIPS 2026" in conf.name
            assert conf.start_date == date(2026, 12, 6)
            assert conf.end_date == date(2026, 12, 12)
            assert conf.cfp_deadline == date(2026, 5, 22)
            assert "Vancouver" in conf.city
            assert "Canada" in conf.country
            assert conf.verification_status == "verified"
            assert "Researchers" in conf.target_audiences
