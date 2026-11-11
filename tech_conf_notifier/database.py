from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, date, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from sqlalchemy import (
    create_engine, Column, String, Text, Date, Time, Float, Integer,
    Boolean, DateTime, JSON, ForeignKey, UniqueConstraint, event, Index
)
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session, Session
from sqlalchemy.pool import QueuePool

from tech_conf_notifier.models import Conference

logger = logging.getLogger("tech_conf_notifier.database")

Base = declarative_base()


class EventModel(Base):
    __tablename__ = "events"

    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), nullable=False, index=True)
    series_slug = Column(String(100), nullable=True)
    category = Column(String(100), nullable=False, index=True)
    subcategory = Column(String(100), nullable=True)
    secondary_categories = Column(JSON, default=list)
    description = Column(Text, default="Not available")
    organizer = Column(String(255), default="Not announced")
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=True)
    start_time = Column(String(50), default="Not announced")
    timezone = Column(String(50), default="Asia/Manila")
    location = Column(String(255), default="Not announced")
    city = Column(String(100), default="Not announced", index=True)
    country = Column(String(100), default="Not announced", index=True)
    iso_country = Column(String(10), nullable=True)
    geographic_tier = Column(String(30), default="international", index=True)
    format = Column(String(20), default="in_person", index=True)
    event_type = Column(String(30), default="conference")
    url = Column(String(1024), nullable=False)
    registration_url = Column(String(1024), nullable=True)
    registration_deadline = Column(Date, nullable=True)
    cfp_deadline = Column(Date, nullable=True)
    cfp_url = Column(String(1024), nullable=True)
    fee_type = Column(String(20), default="unknown")
    fee_amount = Column(String(100), default="Not announced")
    status = Column(String(20), default="scheduled", index=True)
    verification_status = Column(String(20), default="unverified", index=True)
    confidence_score = Column(Float, default=0.5)
    target_audiences = Column(JSON, default=lambda: ["Developers"])
    sources = Column(JSON, default=list)
    metadata_json = Column(JSON, default=dict)
    last_checked = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_events_dates", "start_date", "end_date"),
        Index("idx_events_cat_format", "category", "format"),
    )


class BookmarkModel(Base):
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(64), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(64), default="default")
    notes = Column(Text, nullable=True)
    priority = Column(String(20), default="normal")
    custom_reminder_date = Column(Date, nullable=True)
    saved_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_bookmark_event_user"),
    )


class UserPreferencesModel(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_name = Column(String(50), default="default", unique=True)
    categories = Column(JSON, default=lambda: ["all"])
    locations = Column(JSON, default=lambda: ["Philippines"])
    formats = Column(JSON, default=lambda: ["all"])
    channels = Column(JSON, default=lambda: {"desktop": True, "discord": False, "telegram": False, "email": False})
    reminder_intervals = Column(JSON, default=lambda: [7, 3, 1, 0])
    min_days_notice = Column(Integer, default=0)
    days_lookahead = Column(Integer, default=60)
    keywords_include = Column(JSON, default=list)
    keywords_exclude = Column(JSON, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class NotificationHistoryModel(Base):
    __tablename__ = "notification_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(64), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    trigger_type = Column(String(30), nullable=False)
    channel = Column(String(30), nullable=False)
    sent_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    status = Column(String(20), default="success")  # success, failed, skipped
    recipient = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    payload_snapshot = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_notif_hist_lookup", "event_id", "channel", "trigger_type"),
    )


class Database:
    """Manages SQLite database with Write-Ahead Logging (WAL) and scoped sessions."""

    _instance: Optional[Database] = None

    def __init__(self, db_path: str | Path = "tech_conferences.db"):
        self.db_path = Path(db_path)
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"timeout": 30.0, "check_same_thread": False},
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10
        )

        # Enforce SQLite PRAGMAs for concurrency and performance
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode = WAL;")
            cursor.execute("PRAGMA synchronous = NORMAL;")
            cursor.execute("PRAGMA foreign_keys = ON;")
            cursor.execute("PRAGMA busy_timeout = 30000;")
            cursor.close()

        Base.metadata.create_all(self.engine)
        self.SessionFactory = scoped_session(sessionmaker(bind=self.engine, expire_on_commit=False))

    @classmethod
    def get_instance(cls, db_path: str | Path = "tech_conferences.db") -> Database:
        if cls._instance is None:
            cls._instance = cls(db_path)
        return cls._instance

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.SessionFactory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def upsert_conference(self, conf: Conference) -> None:
        """Upsert a conference into the database."""
        with self.session_scope() as session:
            existing = session.query(EventModel).filter_by(id=conf.id).first()
            if existing:
                existing.name = conf.name
                existing.normalized_name = conf.normalized_name
                existing.category = conf.category
                existing.secondary_categories = conf.secondary_categories
                if conf.description != "Not available":
                    existing.description = conf.description
                if conf.organizer != "Not announced":
                    existing.organizer = conf.organizer
                existing.start_date = conf.start_date
                existing.end_date = conf.end_date
                existing.format = conf.format
                existing.city = conf.city
                existing.country = conf.country
                existing.geographic_tier = conf.geographic_tier
                existing.url = conf.url
                if conf.registration_url:
                    existing.registration_url = conf.registration_url
                if conf.cfp_deadline:
                    existing.cfp_deadline = conf.cfp_deadline
                if conf.cfp_url:
                    existing.cfp_url = conf.cfp_url
                existing.fee_type = conf.fee_type
                existing.fee_amount = conf.fee_amount
                existing.status = conf.status
                existing.verification_status = conf.verification_status
                existing.confidence_score = conf.confidence_score
                existing.target_audiences = conf.target_audiences
                existing.sources = conf.sources
                existing.last_checked = datetime.now(timezone.utc)
            else:
                new_event = EventModel(
                    id=conf.id,
                    name=conf.name,
                    normalized_name=conf.normalized_name,
                    series_slug=conf.series_slug,
                    category=conf.category,
                    subcategory=conf.subcategory,
                    secondary_categories=conf.secondary_categories,
                    description=conf.description,
                    organizer=conf.organizer,
                    start_date=conf.start_date,
                    end_date=conf.end_date,
                    start_time=conf.start_time,
                    timezone=conf.timezone,
                    location=conf.location,
                    city=conf.city,
                    country=conf.country,
                    iso_country=conf.iso_country,
                    geographic_tier=conf.geographic_tier,
                    format=conf.format,
                    event_type=conf.event_type,
                    url=conf.url,
                    registration_url=conf.registration_url,
                    registration_deadline=conf.registration_deadline,
                    cfp_deadline=conf.cfp_deadline,
                    cfp_url=conf.cfp_url,
                    fee_type=conf.fee_type,
                    fee_amount=conf.fee_amount,
                    status=conf.status,
                    verification_status=conf.verification_status,
                    confidence_score=conf.confidence_score,
                    target_audiences=conf.target_audiences,
                    sources=conf.sources,
                    metadata_json=conf.metadata,
                    last_checked=datetime.now(timezone.utc)
                )
                session.add(new_event)

    def get_upcoming_events(
        self,
        days_lookahead: int = 60,
        category: Optional[str] = None,
        format_filter: Optional[str] = None,
        country: Optional[str] = None,
        search_query: Optional[str] = None,
        exclude_dead_links: bool = True
    ) -> List[Conference]:
        """Query upcoming conferences with flexible filtering."""
        today = date.today()
        max_date = date.fromordinal(today.toordinal() + days_lookahead)

        with self.session_scope() as session:
            q = session.query(EventModel).filter(
                EventModel.start_date >= today,
                EventModel.start_date <= max_date,
                EventModel.status != "cancelled"
            )

            if exclude_dead_links:
                q = q.filter(EventModel.verification_status != "dead_link")

            if category and category.lower() != "all":
                q = q.filter(EventModel.category == category)

            if format_filter and format_filter.lower() != "all":
                q = q.filter(EventModel.format == format_filter)

            if country and country.lower() != "all":
                if country.lower() == "philippines":
                    q = q.filter(EventModel.geographic_tier == "local_ph")
                else:
                    q = q.filter(EventModel.country.ilike(f"%{country}%"))

            if search_query:
                term = f"%{search_query}%"
                q = q.filter(
                    EventModel.name.ilike(term) |
                    EventModel.description.ilike(term) |
                    EventModel.city.ilike(term) |
                    EventModel.country.ilike(term)
                )

            q = q.order_by(EventModel.start_date.asc())
            rows = q.all()

            results = []
            for r in rows:
                conf = Conference(
                    name=r.name,
                    category=r.category,
                    start_date=r.start_date,
                    end_date=r.end_date,
                    url=r.url,
                    id=r.id,
                    normalized_name=r.normalized_name,
                    description=r.description,
                    organizer=r.organizer,
                    city=r.city,
                    country=r.country,
                    location=r.location,
                    format=r.format,
                    event_type=r.event_type,
                    geographic_tier=r.geographic_tier,
                    registration_url=r.registration_url,
                    cfp_deadline=r.cfp_deadline,
                    cfp_url=r.cfp_url,
                    fee_type=r.fee_type,
                    fee_amount=r.fee_amount,
                    status=r.status,
                    verification_status=r.verification_status,
                    confidence_score=r.confidence_score,
                    target_audiences=r.target_audiences or ["Developers"],
                    sources=r.sources or []
                )
                results.append(conf)
            return results

    def toggle_bookmark(self, event_id: str, user_id: str = "default") -> bool:
        """Toggles bookmark status. Returns True if saved, False if removed."""
        with self.session_scope() as session:
            existing = session.query(BookmarkModel).filter_by(event_id=event_id, user_id=user_id).first()
            if existing:
                session.delete(existing)
                return False
            else:
                new_bm = BookmarkModel(event_id=event_id, user_id=user_id)
                session.add(new_bm)
                return True

    def get_bookmarked_event_ids(self, user_id: str = "default") -> List[str]:
        """Returns list of bookmarked event IDs."""
        with self.session_scope() as session:
            rows = session.query(BookmarkModel.event_id).filter_by(user_id=user_id).all()
            return [r[0] for r in rows]

    def record_notification(self, event_id: str, trigger_type: str, channel: str, status: str = "success", error: Optional[str] = None) -> None:
        """Log a notification attempt into notification_history."""
        with self.session_scope() as session:
            entry = NotificationHistoryModel(
                event_id=event_id,
                trigger_type=trigger_type,
                channel=channel,
                status=status,
                error_message=error,
                sent_at=datetime.now(timezone.utc)
            )
            session.add(entry)

    def is_notified(self, event_id: str, trigger_type: str, channel: str) -> bool:
        """Checks if a notification was already sent successfully for this event, trigger, and channel."""
        with self.session_scope() as session:
            entry = session.query(NotificationHistoryModel).filter_by(
                event_id=event_id,
                trigger_type=trigger_type,
                channel=channel,
                status="success"
            ).first()
            return entry is not None
