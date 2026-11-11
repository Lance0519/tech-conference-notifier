from __future__ import annotations

import logging
import socket
from datetime import datetime, date, timezone
from pathlib import Path
from flask import Flask, jsonify, request, send_file, render_template, Response
from flask_cors import CORS
from typing import Dict, Any

from tech_conf_notifier.config import AppConfig
from tech_conf_notifier.database import Database, EventModel, BookmarkModel, NotificationHistoryModel
from tech_conf_notifier.engine import DiscoveryEngine
from tech_conf_notifier.models import Conference, MANDATORY_CATEGORIES, MANILA_TZ

logger = logging.getLogger("tech_conf_notifier.api")

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = Flask(
    __name__,
    template_folder=str(TEMPLATE_DIR),
    static_folder=str(STATIC_DIR),
    static_url_path="/static"
)
CORS(app)  # Enable CORS for mobile app requests

engine = DiscoveryEngine()
db = Database.get_instance()


@app.route("/", methods=["GET"])
def index():
    """Serve the Mobile Web PWA index page."""
    return render_template("index.html")


@app.route("/manifest.json", methods=["GET"])
def manifest():
    """Serve the Web App Manifest."""
    return send_file(STATIC_DIR / "manifest.json", mimetype="application/manifest+json")


@app.route("/sw.js", methods=["GET"])
def service_worker():
    """Serve the root Service Worker script."""
    return send_file(STATIC_DIR / "sw.js", mimetype="application/javascript")


@app.route("/download/apk", methods=["GET"])
@app.route("/api/download/apk", methods=["GET"])
def download_apk():
    """Serve the compiled standalone Android APK directly to mobile downloaders."""
    apk_path = BASE_DIR / "TechConfNotifier.apk"
    if not apk_path.exists():
        apk_path = BASE_DIR / "android_app" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"

    if apk_path.exists():
        return send_file(
            str(apk_path),
            as_attachment=True,
            download_name="TechConfNotifier.apk",
            mimetype="application/vnd.android.package-archive"
        )
    return jsonify({"status": "error", "message": "APK file not found on server"}), 404


@app.route("/api/events", methods=["GET"])
def get_events():
    """Retrieve upcoming conferences matching mobile query filters."""
    category = request.args.get("category")
    format_filter = request.args.get("format")
    country = request.args.get("country")
    search_query = request.args.get("search")
    days_lookahead = int(request.args.get("days", 90))

    events = db.get_upcoming_events(
        days_lookahead=days_lookahead,
        category=category,
        format_filter=format_filter,
        country=country,
        search_query=search_query
    )

    bookmarked_ids = set(db.get_bookmarked_event_ids())
    response_data = []
    for e in events:
        d = e.to_dict()
        d["is_bookmarked"] = e.id in bookmarked_ids
        response_data.append(d)

    return jsonify({
        "status": "success",
        "total": len(response_data),
        "events": response_data
    })


@app.route("/api/events/<event_id>", methods=["GET"])
def get_event_detail(event_id: str):
    """Retrieve detailed information for a single conference."""
    with db.session_scope() as session:
        r = session.query(EventModel).filter_by(id=event_id).first()
        if not r:
            return jsonify({"status": "error", "message": "Event not found"}), 404

        bookmarked = event_id in db.get_bookmarked_event_ids()
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
        data = conf.to_dict()
        data["is_bookmarked"] = bookmarked
        return jsonify({"status": "success", "event": data})


@app.route("/api/categories", methods=["GET"])
def get_categories():
    """Retrieve the 16 mandatory IT/CS categories with real-time event counts."""
    events = db.get_upcoming_events(days_lookahead=180)
    cat_counts = {cat: 0 for cat in MANDATORY_CATEGORIES}
    for e in events:
        if e.category in cat_counts:
            cat_counts[e.category] += 1

    items = [{"name": cat, "count": cat_counts[cat]} for cat in MANDATORY_CATEGORIES]
    return jsonify({
        "status": "success",
        "categories": items
    })


@app.route("/api/bookmarks", methods=["GET"])
def get_bookmarks():
    """Retrieve list of user's saved/bookmarked events."""
    bookmarked_ids = set(db.get_bookmarked_event_ids())
    events = db.get_upcoming_events(days_lookahead=365)
    saved = [e.to_dict() for e in events if e.id in bookmarked_ids]
    for s in saved:
        s["is_bookmarked"] = True

    return jsonify({
        "status": "success",
        "total": len(saved),
        "events": saved
    })


@app.route("/api/bookmarks/<event_id>", methods=["POST"])
def toggle_bookmark(event_id: str):
    """Toggle bookmark for an event."""
    is_saved = db.toggle_bookmark(event_id)
    return jsonify({
        "status": "success",
        "event_id": event_id,
        "is_bookmarked": is_saved
    })


@app.route("/api/sync", methods=["POST"])
def trigger_sync():
    """Trigger an immediate background discovery run."""
    result = engine.process_and_notify()
    return jsonify({
        "status": "success",
        "message": "Discovery run completed successfully",
        "result": result
    })


@app.route("/api/notifications", methods=["GET"])
def get_notifications():
    """Retrieve recent notifications sent."""
    with db.session_scope() as session:
        rows = session.query(NotificationHistoryModel).order_by(
            NotificationHistoryModel.sent_at.desc()
        ).limit(30).all()

        results = []
        for r in rows:
            results.append({
                "id": r.id,
                "event_id": r.event_id,
                "trigger_type": r.trigger_type,
                "channel": r.channel,
                "sent_at": r.sent_at.isoformat() if r.sent_at else None,
                "status": r.status
            })
        return jsonify({"status": "success", "notifications": results})


@app.route("/api/calendar/<event_id>.ics", methods=["GET"])
def get_calendar_ics(event_id: str):
    """Generate standard iCalendar file for mobile calendar apps."""
    with db.session_scope() as session:
        r = session.query(EventModel).filter_by(id=event_id).first()
        if not r:
            return "Event not found", 404

        s_str = r.start_date.strftime("%Y%m%d")
        e_date = r.end_date or r.start_date
        e_str = e_date.strftime("%Y%m%d")

        ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Tech Conference Notifier//EN
BEGIN:VEVENT
UID:{r.id}@techconfnotifier.org
DTSTAMP:{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}
DTSTART;VALUE=DATE:{s_str}
DTEND;VALUE=DATE:{e_str}
SUMMARY:{r.name}
DESCRIPTION:{r.description}\\n\\nLink: {r.url}
LOCATION:{r.location}, {r.city}, {r.country}
URL:{r.url}
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""

        return Response(
            ics_content,
            mimetype="text/calendar",
            headers={"Content-Disposition": f"attachment; filename={r.id}.ics"}
        )


def get_local_ip() -> str:
    """Detect LAN IPv4 address for mobile access."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def start_server(host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
    """Start the mobile backend server."""
    local_ip = get_local_ip()
    print("=" * 68)
    print("  TECH CONFERENCES & CONVENTIONS NOTIFIER - MOBILE APP & REST API")
    print("=" * 68)
    print(f"  Local Access:      http://localhost:{port}")
    print(f"  Mobile LAN Access: http://{local_ip}:{port}")
    print("=" * 68)
    print("  Mobile Setup:")
    print(f"  1. Ensure your phone is connected to the same Wi-Fi network.")
    print(f"  2. Open http://{local_ip}:{port} on your mobile browser (Safari/Chrome).")
    print(f"  3. Tap 'Share' or '...' -> 'Add to Home Screen' to install PWA.")
    print("=" * 68 + "\n")
    logger.info(f"Starting Mobile API Backend on http://{host}:{port}")
    # Populate initial cache if empty
    if len(db.get_upcoming_events(days_lookahead=365)) == 0:
        logger.info("Initializing conference catalog...")
        engine.run_discovery()
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    start_server()
