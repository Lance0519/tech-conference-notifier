from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import List

from tech_conf_notifier.models import Conference
from tech_conf_notifier.notifiers.base import BaseNotifier

logger = logging.getLogger("tech_conf_notifier.notifiers.digest")


class DigestNotifier(BaseNotifier):
    """Generates local standalone HTML and Markdown digest reports."""

    def __init__(self, output_html: str = "upcoming_conferences.html", output_markdown: str = "upcoming_conferences.md"):
        self.output_html = output_html
        self.output_markdown = output_markdown

    @property
    def name(self) -> str:
        return "digest"

    def notify(self, conferences: List[Conference]) -> bool:
        try:
            live_confs = [c for c in conferences if c.verification_status != "dead_link"]
            self._write_markdown(live_confs)
            self._write_html(live_confs)
            return True
        except Exception as e:
            logger.error(f"Failed to generate digest files: {e}")
            return False

    def test_notification(self) -> bool:
        sample = [Conference(
            name="Sample Global Tech Summit 2026",
            category="Information Technology",
            start_date=datetime.now().date(),
            url="https://example.com"
        )]
        return self.notify(sample)

    def _write_markdown(self, conferences: List[Conference]) -> None:
        now_str = datetime.now().strftime("%B %d, %Y %I:%M %p")
        lines = [
            "# 🔔 Upcoming IT, Computer Science & Technology Conferences",
            f"*Generated on {now_str}*\n",
            "> 🎓 **Student-Friendly Guarantee:** All listed conferences welcome students, learners, and aspiring tech enthusiasts alongside industry professionals! Look for student discount passes, academic tracks, and volunteer opportunities.\n",
            "| Event Name | Category | Date | Location | Format | Status | Official Link |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
        ]

        for c in conferences:
            flag = "🇵🇭 " if c.is_philippines else ""
            fmt = c.format.capitalize()
            student_tag = " 🎓 *(Student-Friendly)*" if c.is_student_friendly else ""
            lines.append(
                f"| **{c.name}**{student_tag} | {c.category} | {c.formatted_date_range} | {flag}{c.location_str} | {fmt} | {c.status_label} | [Visit Site]({c.url}) |"
            )

        with open(self.output_markdown, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def _write_html(self, conferences: List[Conference]) -> None:
        now_str = datetime.now().strftime("%B %d, %Y %I:%M %p")
        cards_html = ""

        for c in conferences:
            flag = "🇵🇭 " if c.is_philippines else "🌐 "
            badge_color = "#3b82f6"
            if c.category in ("Artificial Intelligence and Machine Learning", "Data Science and Analytics"):
                badge_color = "#8b5cf6"
            elif c.category == "Cybersecurity":
                badge_color = "#ef4444"
            elif c.category == "Cloud Computing and DevOps":
                badge_color = "#06b6d4"

            cfp_html = f"<div class='cfp'>📝 CFP: {c.cfp_deadline.strftime('%b %d, %Y')}</div>" if c.cfp_deadline else ""
            fee_html = f"<span class='fee'>{c.fee_amount}</span>" if c.fee_amount != "Not announced" else ""
            student_badge = "<span class='badge' style='background:#10b98122; color:#10b981; border:1px solid #10b98144;'>🎓 Student Friendly</span>" if c.is_student_friendly else ""

            cards_html += f"""
            <div class="card" data-category="{c.category}" data-country="{c.country}">
                <div class="card-header">
                    <span class="badge" style="background:{badge_color}22; color:{badge_color}; border:1px solid {badge_color}44;">{c.category}</span>
                    {student_badge}
                    <span class="status">{c.status_label}</span>
                </div>
                <h3>{c.name}</h3>
                <div class="meta">
                    <div>📅 {c.formatted_date_range}</div>
                    <div>📍 {flag}{c.location_str}</div>
                    <div>🎓 Eligibility: Student-Friendly (Students & Pros Welcome)</div>
                    <div>🏢 {c.organizer}</div>
                </div>
                <p class="desc">{c.description if c.description != 'Not available' else ''}</p>
                <div class="card-footer">
                    {cfp_html}
                    {fee_html}
                    <a href="{c.url}" target="_blank" rel="noopener noreferrer" class="btn">View Official Website &rarr;</a>
                </div>
            </div>
            """

        html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Upcoming IT & Tech Conferences</title>
    <style>
        :root {{
            --bg: #0f172a;
            --surface: #1e293b;
            --border: #334155;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #38bdf8;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 24px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        header {{
            text-align: center;
            margin-bottom: 32px;
        }}
        h1 {{
            color: var(--accent);
            margin-bottom: 8px;
        }}
        .search-bar {{
            display: flex;
            gap: 12px;
            margin-bottom: 24px;
        }}
        input[type="text"] {{
            flex: 1;
            padding: 12px 16px;
            border-radius: 8px;
            border: 1px solid var(--border);
            background: var(--surface);
            color: var(--text);
            font-size: 16px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }}
        .card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}
        .badge {{
            font-size: 12px;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 9999px;
        }}
        .status {{
            font-size: 12px;
            font-weight: 600;
            color: #10b981;
        }}
        h3 {{
            margin: 0 0 12px 0;
            font-size: 18px;
        }}
        .meta {{
            color: var(--text-muted);
            font-size: 14px;
            display: flex;
            flex-direction: column;
            gap: 6px;
            margin-bottom: 12px;
        }}
        .desc {{
            font-size: 13px;
            color: var(--text-muted);
            line-height: 1.5;
            margin-bottom: 16px;
            flex-grow: 1;
        }}
        .card-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid var(--border);
            padding-top: 12px;
        }}
        .btn {{
            background: var(--accent);
            color: #0f172a;
            padding: 8px 16px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 600;
            font-size: 13px;
        }}
        .cfp {{
            font-size: 12px;
            color: #f59e0b;
        }}
        .fee {{
            font-size: 12px;
            color: var(--text-muted);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div style="display:flex; justify-content:center; align-items:center; gap:12px; margin-bottom:8px;">
                <img src="static/logo.jpg" alt="Logo" style="width:48px; height:48px; border-radius:12px; border:2px solid var(--accent); object-fit:cover;">
                <h1 style="margin:0;">Upcoming IT, Computer Science & Tech Conferences</h1>
            </div>
            <p style="color:var(--text-muted);">Discovered automatically &bull; Last updated {now_str}</p>
        </header>
        <div style="background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.3); border-radius:12px; padding:14px 20px; margin-bottom:24px; display:flex; align-items:center; gap:14px;">
            <span style="font-size:26px;">🎓</span>
            <div>
                <strong style="color:#10b981; font-size:15px;">Student-Friendly Conferences:</strong>
                <span style="color:#cbd5e1; font-size:14px;"> All listed conferences are open to students, researchers, and learners &mdash; not for industry professionals only! Look out for student discount passes, academic tracks, and volunteer perks.</span>
            </div>
        </div>
        <div class="search-bar">
            <input type="text" id="searchInput" placeholder="Search conferences, topics, cities, or countries..." onkeyup="filterCards()">
        </div>
        <div class="grid" id="cardGrid">
            {cards_html}
        </div>
    </div>
    <script>
        function filterCards() {{
            const query = document.getElementById('searchInput').value.toLowerCase();
            const cards = document.querySelectorAll('.card');
            cards.forEach(card => {{
                const text = card.innerText.toLowerCase();
                card.style.display = text.includes(query) ? 'flex' : 'none';
            }});
        }}
    </script>
</body>
</html>
        """
        with open(self.output_html, "w", encoding="utf-8") as f:
            f.write(html_doc)
