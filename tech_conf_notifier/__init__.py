"""
IT & Tech Conference Automated Notifier System
===============================================
A modular, automated system to discover upcoming IT, Computer Science,
and Technology conferences/conventions and notify the user via Windows Toasts,
Discord Webhooks, Telegram, Email, and local digests.
"""

__version__ = "1.0.0"
__author__ = "Tech Conference Notifier"

from tech_conf_notifier.config import AppConfig
from tech_conf_notifier.database import Database
from tech_conf_notifier.engine import DiscoveryEngine
from tech_conf_notifier.models import Conference, MANILA_TZ, MANDATORY_CATEGORIES
from tech_conf_notifier.scheduler import ConferenceScheduler, SchedulerLock
from tech_conf_notifier.task_installer import WindowsTaskScheduler

__all__ = [
    "AppConfig",
    "Database",
    "DiscoveryEngine",
    "Conference",
    "MANILA_TZ",
    "MANDATORY_CATEGORIES",
    "ConferenceScheduler",
    "SchedulerLock",
    "WindowsTaskScheduler"
]
