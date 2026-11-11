from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml


@dataclass
class DesktopNotifierConfig:
    enabled: bool = True
    max_toasts: int = 5
    sound: bool = True


@dataclass
class DiscordNotifierConfig:
    enabled: bool = False
    webhook_url: str = ""
    mention_role: Optional[str] = None


@dataclass
class TelegramNotifierConfig:
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""


@dataclass
class EmailNotifierConfig:
    enabled: bool = False
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender_email: str = ""
    sender_password: str = ""  # App Password for Gmail
    recipient_email: str = ""
    use_tls: bool = True


@dataclass
class DigestNotifierConfig:
    enabled: bool = True
    output_html: str = "upcoming_conferences.html"
    output_markdown: str = "upcoming_conferences.md"


@dataclass
class NotifiersConfig:
    desktop: DesktopNotifierConfig = field(default_factory=DesktopNotifierConfig)
    discord: DiscordNotifierConfig = field(default_factory=DiscordNotifierConfig)
    telegram: TelegramNotifierConfig = field(default_factory=TelegramNotifierConfig)
    email: EmailNotifierConfig = field(default_factory=EmailNotifierConfig)
    digest: DigestNotifierConfig = field(default_factory=DigestNotifierConfig)


@dataclass
class ScheduleConfig:
    interval_hours: int = 24
    run_at_time: str = "09:00"  # HH:MM for daily schedule in daemon mode
    auto_start_on_boot: bool = False


@dataclass
class AppConfig:
    topics: List[str] = field(default_factory=lambda: [
        "all"  # or specific: "general", "security", "devops", "python", "javascript", "data", "ai", "cloud", "mobile"
    ])
    days_lookahead: int = 60  # Only show conferences in the next N days
    min_days_notice: int = 0  # Alert if starts in >= min_days_notice
    format_filter: str = "all"  # "all", "online", "in_person"
    country_filter: List[str] = field(default_factory=list)  # Empty means any country
    keywords: List[str] = field(default_factory=list)  # Filter by keywords in name or description
    include_academic: bool = True  # Include CCF-Deadlines academic/research CS conferences
    remind_days_before: List[int] = field(default_factory=lambda: [7, 1])  # Re-notify 7 days & 1 day before
    notifiers: NotifiersConfig = field(default_factory=NotifiersConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    custom_conferences_file: str = "custom_conferences.json"
    cache_ttl_hours: int = 12

    @classmethod
    def load(cls, config_path: str | Path = "config.yaml") -> AppConfig:
        path = Path(config_path)
        if not path.exists():
            config = cls()
            config.save(path)
            return config

        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        # Parse nested dataclasses safely
        notif_raw = raw.get("notifiers", {})
        desktop_cfg = DesktopNotifierConfig(**notif_raw.get("desktop", {}))
        discord_cfg = DiscordNotifierConfig(**notif_raw.get("discord", {}))
        telegram_cfg = TelegramNotifierConfig(**notif_raw.get("telegram", {}))
        email_cfg = EmailNotifierConfig(**notif_raw.get("email", {}))
        digest_cfg = DigestNotifierConfig(**notif_raw.get("digest", {}))

        notifiers = NotifiersConfig(
            desktop=desktop_cfg,
            discord=discord_cfg,
            telegram=telegram_cfg,
            email=email_cfg,
            digest=digest_cfg
        )

        sched_raw = raw.get("schedule", {})
        schedule = ScheduleConfig(**sched_raw)

        return cls(
            topics=raw.get("topics", ["all"]),
            days_lookahead=raw.get("days_lookahead", 60),
            min_days_notice=raw.get("min_days_notice", 0),
            format_filter=raw.get("format_filter", "all"),
            country_filter=raw.get("country_filter", []),
            keywords=raw.get("keywords", []),
            include_academic=raw.get("include_academic", True),
            remind_days_before=raw.get("remind_days_before", [7, 1]),
            notifiers=notifiers,
            schedule=schedule,
            custom_conferences_file=raw.get("custom_conferences_file", "custom_conferences.json"),
            cache_ttl_hours=raw.get("cache_ttl_hours", 12)
        )

    def save(self, config_path: str | Path = "config.yaml") -> None:
        data = {
            "topics": self.topics,
            "days_lookahead": self.days_lookahead,
            "min_days_notice": self.min_days_notice,
            "format_filter": self.format_filter,
            "country_filter": self.country_filter,
            "keywords": self.keywords,
            "include_academic": self.include_academic,
            "remind_days_before": self.remind_days_before,
            "custom_conferences_file": self.custom_conferences_file,
            "cache_ttl_hours": self.cache_ttl_hours,
            "schedule": {
                "interval_hours": self.schedule.interval_hours,
                "run_at_time": self.schedule.run_at_time,
                "auto_start_on_boot": self.schedule.auto_start_on_boot,
            },
            "notifiers": {
                "desktop": {
                    "enabled": self.notifiers.desktop.enabled,
                    "max_toasts": self.notifiers.desktop.max_toasts,
                    "sound": self.notifiers.desktop.sound,
                },
                "discord": {
                    "enabled": self.notifiers.discord.enabled,
                    "webhook_url": self.notifiers.discord.webhook_url,
                    "mention_role": self.notifiers.discord.mention_role,
                },
                "telegram": {
                    "enabled": self.notifiers.telegram.enabled,
                    "bot_token": self.notifiers.telegram.bot_token,
                    "chat_id": self.notifiers.telegram.chat_id,
                },
                "email": {
                    "enabled": self.notifiers.email.enabled,
                    "smtp_server": self.notifiers.email.smtp_server,
                    "smtp_port": self.notifiers.email.smtp_port,
                    "sender_email": self.notifiers.email.sender_email,
                    "sender_password": self.notifiers.email.sender_password,
                    "recipient_email": self.notifiers.email.recipient_email,
                    "use_tls": self.notifiers.email.use_tls,
                },
                "digest": {
                    "enabled": self.notifiers.digest.enabled,
                    "output_html": self.notifiers.digest.output_html,
                    "output_markdown": self.notifiers.digest.output_markdown,
                }
            }
        }
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
