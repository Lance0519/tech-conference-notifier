from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from zoneinfo import ZoneInfo

# Manila Timezone Anchor
MANILA_TZ = ZoneInfo("Asia/Manila")

MANDATORY_CATEGORIES = [
    "Computer Science",
    "Information Technology",
    "Software Engineering",
    "Artificial Intelligence and Machine Learning",
    "Data Science and Analytics",
    "Cybersecurity",
    "Networking and Telecommunications",
    "Cloud Computing and DevOps",
    "Web and Mobile Development",
    "Game Development",
    "Robotics and Internet of Things",
    "Information Systems",
    "Database Management",
    "Computer Engineering",
    "Emerging Technologies",
    "Technology Entrepreneurship and Innovation",
]

TARGET_AUDIENCE_PERSONAS = [
    "Students",
    "Developers",
    "Researchers",
    "IT Executives",
    "General Public"
]


def normalize_text_for_id(text: str) -> str:
    """Normalize text by lowercasing and stripping punctuation and recurring years."""
    t = text.lower().strip()
    t = re.sub(r"\b20\d{2}\b", "", t)
    t = re.sub(r"[^\w\s]", "", t)
    return " ".join(t.split())


@dataclass
class Conference:
    name: str
    category: str = "Information Technology"
    source: str = "unknown"
    start_date: date = field(default_factory=date.today)
    url: str = ""
    id: str = ""
    normalized_name: str = ""
    series_slug: Optional[str] = None
    subcategory: Optional[str] = None
    secondary_categories: List[str] = field(default_factory=list)
    description: str = "Not available"
    organizer: str = "Not announced"
    end_date: Optional[date] = None
    start_time: Optional[str] = "Not announced"
    timezone: str = "Asia/Manila"
    location: str = "Not announced"
    city: str = "Not announced"
    country: str = "Not announced"
    iso_country: Optional[str] = None
    geographic_tier: str = "international"  # "local_ph", "sea_asean", "international"
    format: str = "in_person"  # "in_person", "virtual", "hybrid"
    event_type: str = "conference"  # "conference", "convention", "summit", "workshop", "hackathon", "meetup"
    registration_url: Optional[str] = None
    registration_deadline: Optional[date] = None
    cfp_deadline: Optional[date] = None
    cfp_url: Optional[str] = None
    fee_type: str = "unknown"  # "free", "paid", "unknown"
    fee_amount: str = "Not announced"
    status: str = "scheduled"  # "scheduled", "ongoing", "postponed", "rescheduled", "cancelled", "completed"
    verification_status: str = "unverified"  # "verified", "provisional", "unverified", "dead_link"
    confidence_score: float = 0.5
    target_audiences: List[str] = field(default_factory=lambda: ["Developers"])
    eligibility: str = "Open to Students & Professionals (Student-Friendly)"
    is_student_friendly: bool = True
    sources: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_checked: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(MANILA_TZ))
    updated_at: datetime = field(default_factory=lambda: datetime.now(MANILA_TZ))

    def __post_init__(self):
        if not self.normalized_name:
            self.normalized_name = normalize_text_for_id(self.name)
        
        # Enforce Philippines geographic tier
        c_lower = (self.country or "").lower()
        city_lower = (self.city or "").lower()
        if "philippines" in c_lower or "ph" == self.iso_country or any(
            p in city_lower for p in ["manila", "cebu", "davao", "taguig", "makati", "pasig", "quezon city", "baguio"]
        ):
            self.geographic_tier = "local_ph"
            if self.country == "Not announced" or not self.country:
                self.country = "Philippines"
                self.iso_country = "PH"
        elif any(sea in c_lower for sea in ["singapore", "malaysia", "indonesia", "thailand", "vietnam"]):
            self.geographic_tier = "sea_asean"

        # Deterministic Canonical Cluster ID
        if not self.id:
            s_date_str = self.start_date.isoformat() if self.start_date else "nodate"
            clean_url = re.sub(r"^https?://(www\.)?", "", self.url.lower())
            clean_url = clean_url.split("?")[0].split("#")[0].rstrip("/")
            raw_key = f"{self.normalized_name}_{s_date_str}_{clean_url}"
            self.id = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]

    @property
    def is_online(self) -> bool:
        return self.format in ("virtual", "hybrid")

    @property
    def is_philippines(self) -> bool:
        return self.geographic_tier == "local_ph"

    @property
    def is_free(self) -> bool:
        return self.fee_type == "free" or "free" in self.fee_amount.lower()

    @property
    def has_cfp_open(self) -> bool:
        if not self.cfp_deadline:
            return False
        today = datetime.now(MANILA_TZ).date()
        return self.cfp_deadline >= today

    @property
    def days_until(self) -> int:
        today = datetime.now(MANILA_TZ).date()
        return (self.start_date - today).days

    @property
    def status_label(self) -> str:
        if self.status == "cancelled":
            return "CANCELLED"
        if self.status == "postponed":
            return "POSTPONED"
        if self.status == "rescheduled":
            return "RESCHEDULED"
            
        d = self.days_until
        if d < 0:
            if self.end_date and (self.end_date - datetime.now(MANILA_TZ).date()).days >= 0:
                return "Happening Now (Ongoing)"
            return f"Passed {abs(d)} day{'s' if abs(d) != 1 else ''} ago"
        elif d == 0:
            return "Starts TODAY!"
        elif d == 1:
            return "Starts TOMORROW!"
        elif d <= 7:
            return f"Starts in {d} days (This Week)"
        elif d <= 14:
            return f"Starts in {d} days (Next Week)"
        elif d <= 30:
            return f"Starts in {d} days (~1 month)"
        else:
            return f"Starts in {d} days"

    @property
    def location_str(self) -> str:
        parts = []
        if self.city and self.city != "Not announced":
            parts.append(self.city.strip())
        if self.country and self.country != "Not announced":
            parts.append(self.country.strip())
        loc = ", ".join(parts) if parts else "Location TBA"

        if self.format == "hybrid":
            return f"Hybrid ({loc} + Online)"
        elif self.format == "virtual":
            return "Online / Virtual"
        return loc

    @property
    def formatted_date_range(self) -> str:
        if not self.end_date or self.end_date == self.start_date:
            return self.start_date.strftime("%b %d, %Y")
        
        if self.start_date.year == self.end_date.year and self.start_date.month == self.end_date.month:
            return f"{self.start_date.strftime('%b %d')}-{self.end_date.strftime('%d, %Y')}"
        elif self.start_date.year == self.end_date.year:
            return f"{self.start_date.strftime('%b %d')} - {self.end_date.strftime('%b %d, %Y')}"
        else:
            return f"{self.start_date.strftime('%b %d, %Y')} - {self.end_date.strftime('%b %d, %Y')}"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["start_date"] = self.start_date.isoformat() if self.start_date else None
        d["end_date"] = self.end_date.isoformat() if self.end_date else None
        d["registration_deadline"] = self.registration_deadline.isoformat() if self.registration_deadline else None
        d["cfp_deadline"] = self.cfp_deadline.isoformat() if self.cfp_deadline else None
        d["last_checked"] = self.last_checked.isoformat() if self.last_checked else None
        d["created_at"] = self.created_at.isoformat() if self.created_at else None
        d["updated_at"] = self.updated_at.isoformat() if self.updated_at else None
        d["location_str"] = self.location_str
        d["formatted_date"] = self.formatted_date_range
        d["days_until"] = self.days_until
        d["status_label"] = self.status_label
        d["is_online"] = self.is_online
        d["is_philippines"] = self.is_philippines
        d["is_free"] = self.is_free
        d["has_cfp_open"] = self.has_cfp_open
        d["eligibility"] = self.eligibility
        d["is_student_friendly"] = self.is_student_friendly
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Conference:
        s_date = datetime.strptime(data["start_date"], "%Y-%m-%d").date() if data.get("start_date") else date.today()
        e_date = datetime.strptime(data["end_date"], "%Y-%m-%d").date() if data.get("end_date") else None
        reg_dead = datetime.strptime(data["registration_deadline"], "%Y-%m-%d").date() if data.get("registration_deadline") else None
        cfp_dead = datetime.strptime(data["cfp_deadline"], "%Y-%m-%d").date() if data.get("cfp_deadline") else None

        # Format backward compatibility
        fmt = data.get("format")
        if not fmt:
            fmt = "virtual" if data.get("is_online") else "in_person"

        cat = data.get("category") or data.get("topic") or "Information Technology"

        return cls(
            name=data["name"],
            category=cat,
            source=data.get("source", "unknown"),
            start_date=s_date,
            url=data.get("url", ""),
            id=data.get("id", ""),
            normalized_name=data.get("normalized_name", ""),
            series_slug=data.get("series_slug"),
            subcategory=data.get("subcategory"),
            secondary_categories=data.get("secondary_categories", []),
            description=data.get("description", "Not available"),
            organizer=data.get("organizer", "Not announced"),
            end_date=e_date,
            start_time=data.get("start_time", "Not announced"),
            timezone=data.get("timezone", "Asia/Manila"),
            location=data.get("location", "Not announced"),
            city=data.get("city", "Not announced"),
            country=data.get("country", "Not announced"),
            iso_country=data.get("iso_country"),
            geographic_tier=data.get("geographic_tier", "international"),
            format=fmt,
            event_type=data.get("event_type", "conference"),
            registration_url=data.get("registration_url"),
            registration_deadline=reg_dead,
            cfp_deadline=cfp_dead,
            cfp_url=data.get("cfp_url"),
            fee_type=data.get("fee_type", "unknown"),
            fee_amount=data.get("fee_amount", "Not announced"),
            status=data.get("status", "scheduled"),
            verification_status=data.get("verification_status", "unverified"),
            confidence_score=float(data.get("confidence_score", 0.5)),
            target_audiences=data.get("target_audiences", ["Developers"]),
            eligibility=data.get("eligibility", "Open to Students & Professionals (Student-Friendly)"),
            is_student_friendly=bool(data.get("is_student_friendly", True)),
            sources=data.get("sources", []),
            metadata=data.get("metadata", {})
        )
