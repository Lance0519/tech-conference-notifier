from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional

from tech_conf_notifier.config import AppConfig
from tech_conf_notifier.database import Database
from tech_conf_notifier.fetchers import (
    ConfsTechFetcher, CCFDeadlinesFetcher, CustomJsonFetcher, RegionalPHFetcher
)
from tech_conf_notifier.models import Conference, MANILA_TZ
from tech_conf_notifier.notifiers import (
    DesktopToastNotifier, DiscordNotifier, TelegramNotifier, EmailNotifier, DigestNotifier
)
from tech_conf_notifier.verification import EventVerifier

logger = logging.getLogger("tech_conf_notifier.engine")


class DiscoveryEngine:
    """
    Central Coordinator for the IT/Tech Conference Discovery and Notification Pipeline.
    Manages multi-source fetching, deduplication, database storage, and notification dispatch.
    """

    def __init__(self, config: Optional[AppConfig] = None, db_path: str = "tech_conferences.db"):
        self.config = config or AppConfig.load()
        self.db = Database.get_instance(db_path)
        self.fetchers = [
            RegionalPHFetcher(),
            ConfsTechFetcher(cache_ttl_hours=self.config.cache_ttl_hours),
            CCFDeadlinesFetcher(cache_ttl_hours=self.config.cache_ttl_hours),
            CustomJsonFetcher(json_path=self.config.custom_conferences_file)
        ]
        self._init_notifiers()

    def _init_notifiers(self):
        self.notifiers = []

        # Desktop
        if self.config.notifiers.desktop.enabled:
            self.notifiers.append(DesktopToastNotifier(
                max_toasts=self.config.notifiers.desktop.max_toasts
            ))

        # Discord
        if self.config.notifiers.discord.enabled and self.config.notifiers.discord.webhook_url:
            self.notifiers.append(DiscordNotifier(
                webhook_url=self.config.notifiers.discord.webhook_url,
                mention_role=self.config.notifiers.discord.mention_role
            ))

        # Telegram
        if self.config.notifiers.telegram.enabled and self.config.notifiers.telegram.bot_token and self.config.notifiers.telegram.chat_id:
            self.notifiers.append(TelegramNotifier(
                bot_token=self.config.notifiers.telegram.bot_token,
                chat_id=self.config.notifiers.telegram.chat_id
            ))

        # Email
        if self.config.notifiers.email.enabled and self.config.notifiers.email.sender_email and self.config.notifiers.email.recipient_email:
            self.notifiers.append(EmailNotifier(
                smtp_server=self.config.notifiers.email.smtp_server,
                smtp_port=self.config.notifiers.email.smtp_port,
                sender_email=self.config.notifiers.email.sender_email,
                sender_password=self.config.notifiers.email.sender_password,
                recipient_email=self.config.notifiers.email.recipient_email,
                use_tls=self.config.notifiers.email.use_tls
            ))

        # Digest
        if self.config.notifiers.digest.enabled:
            self.notifiers.append(DigestNotifier(
                output_html=self.config.notifiers.digest.output_html,
                output_markdown=self.config.notifiers.digest.output_markdown
            ))

    def run_discovery(self) -> List[Conference]:
        """
        Executes an end-to-end event discovery, verification, and deduplication run.
        Returns the unified list of upcoming conferences.
        """
        today = datetime.now(MANILA_TZ).date()
        end_date = today + timedelta(days=self.config.days_lookahead)

        raw_events: List[Conference] = []
        for fetcher in self.fetchers:
            try:
                events = fetcher.fetch(start_date=today, end_date=end_date, topics=self.config.topics)
                logger.info(f"Fetcher {fetcher.name} discovered {len(events)} events")
                raw_events.extend(events)
            except Exception as e:
                logger.error(f"Error in fetcher {fetcher.name}: {e}")

        # Deduplication and clustering
        clustered_events: List[Conference] = []
        for candidate in raw_events:
            candidate = EventVerifier.sanitize_sentinels(candidate)
            matched = False
            for existing in clustered_events:
                if EventVerifier.are_duplicates(existing, candidate):
                    EventVerifier.merge_events(existing, candidate)
                    matched = True
                    break
            if not matched:
                clustered_events.append(candidate)

        # Sort: Philippines first, then chronologically by start date
        def sort_key(c: Conference):
            is_ph_priority = 0 if c.is_philippines else 1
            return (is_ph_priority, c.start_date)

        clustered_events.sort(key=sort_key)

        # Persist to database
        for conf in clustered_events:
            self.db.upsert_conference(conf)

        logger.info(f"Total unified upcoming conferences: {len(clustered_events)}")
        return clustered_events

    def process_and_notify(self) -> Dict[str, Any]:
        """
        Performs full discovery, evaluates notification triggers, dispatches alerts,
        and generates digest files.
        """
        conferences = self.run_discovery()
        conferences = [c for c in conferences if c.verification_status != "dead_link"]
        today = datetime.now(MANILA_TZ).date()

        alerts_to_send: List[Conference] = []

        for conf in conferences:
            # Trigger 1: Newly discovered event
            if not self.db.is_notified(conf.id, "initial", "global"):
                alerts_to_send.append(conf)
                self.db.record_notification(conf.id, "initial", "global", "success")
                continue

            # Trigger 2: Milestone reminders (e.g. 7, 3, 1, 0 days before start)
            d_until = conf.days_until
            for milestone in [7, 3, 1, 0]:
                if d_until == milestone:
                    m_key = f"reminder_{milestone}d"
                    if not self.db.is_notified(conf.id, m_key, "global"):
                        alerts_to_send.append(conf)
                        self.db.record_notification(conf.id, m_key, "global", "success")
                        break

            # Trigger 3: CFP Deadlines (e.g. 14, 7, 3, 1 days before CFP close)
            if conf.cfp_deadline:
                cfp_days = (conf.cfp_deadline - today).days
                for cfp_milestone in [14, 7, 3, 1]:
                    if cfp_days == cfp_milestone:
                        c_key = f"cfp_{cfp_milestone}d"
                        if not self.db.is_notified(conf.id, c_key, "global"):
                            alerts_to_send.append(conf)
                            self.db.record_notification(conf.id, c_key, "global", "success")
                            break

        # Dispatch alerts
        dispatch_results = {}
        for notifier in self.notifiers:
            # Digest always receives all current upcoming conferences
            if notifier.name == "digest":
                res = notifier.notify(conferences)
            else:
                res = notifier.notify(alerts_to_send) if alerts_to_send else True
            dispatch_results[notifier.name] = res

        return {
            "total_conferences": len(conferences),
            "alerts_sent": len(alerts_to_send),
            "dispatches": dispatch_results
        }

    def verify_all_urls(self, timeout: int = 6) -> Dict[str, Any]:
        """
        Actively verifies that all upcoming conferences have live, reachable official URLs.
        Updates status to 'verified' or 'dead_link'.
        """
        conferences = self.db.get_upcoming_events(days_lookahead=365, exclude_dead_links=False)
        results = {"total": len(conferences), "verified": 0, "dead": 0, "details": []}

        for c in conferences:
            if not c.url or not c.url.startswith("http"):
                c.verification_status = "dead_link"
                self.db.upsert_conference(c)
                results["dead"] += 1
                results["details"].append({"name": c.name, "url": c.url, "status": "missing_url", "code": None})
                continue

            is_alive, final_url, status_code = EventVerifier.verify_url_health(c.url, timeout=timeout)
            if is_alive:
                c.verification_status = "verified"
                if final_url and final_url != c.url:
                    c.url = final_url
                self.db.upsert_conference(c)
                results["verified"] += 1
                results["details"].append({"name": c.name, "url": c.url, "status": "ok", "code": status_code})
            else:
                c.verification_status = "dead_link"
                self.db.upsert_conference(c)
                results["dead"] += 1
                results["details"].append({"name": c.name, "url": c.url, "status": "dead", "code": status_code})

        return results
