from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

from tech_conf_notifier.models import Conference
from tech_conf_notifier.notifiers.base import BaseNotifier

logger = logging.getLogger("tech_conf_notifier.notifiers.email")


class EmailNotifier(BaseNotifier):
    """Dispatches responsive HTML email notifications via SMTP."""

    def __init__(
        self,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 587,
        sender_email: str = "",
        sender_password: str = "",
        recipient_email: str = "",
        use_tls: bool = True
    ):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipient_email = recipient_email
        self.use_tls = use_tls

    @property
    def name(self) -> str:
        return "email"

    def _build_html(self, conferences: List[Conference]) -> str:
        rows_html = ""
        for c in conferences:
            flag = "🇵🇭 " if c.is_philippines else ""
            cfp_badge = f"<span style='background:#f39c12;color:#fff;padding:2px 8px;border-radius:4px;font-size:12px;'>CFP Deadline: {c.cfp_deadline.strftime('%b %d')}</span>" if c.cfp_deadline else ""
            
            rows_html += f"""
            <div style="background:#ffffff; border-radius:8px; padding:16px; margin-bottom:16px; border:1px solid #e1e4e8; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="background:#e8f0fe; color:#1a73e8; font-weight:bold; font-size:12px; padding:4px 8px; border-radius:12px;">{c.category}</span>
                    <span style="color:#28a745; font-weight:bold; font-size:12px;">{c.status_label}</span>
                </div>
                <h3 style="margin:10px 0 6px 0; color:#202124;"><a href="{c.url}" style="color:#1a73e8; text-decoration:none;">{c.name}</a></h3>
                <p style="margin:4px 0; color:#5f6368; font-size:14px;">📅 <strong>Date:</strong> {c.formatted_date_range}</p>
                <p style="margin:4px 0; color:#5f6368; font-size:14px;">📍 <strong>Location:</strong> {flag}{c.location_str}</p>
                <p style="margin:8px 0 12px 0; color:#3c4043; font-size:13px; line-height:1.4;">{c.description if c.description != 'Not available' else ''}</p>
                <div>
                    {cfp_badge}
                    <a href="{c.url}" style="display:inline-block; background:#1a73e8; color:#ffffff; padding:6px 14px; text-decoration:none; border-radius:4px; font-size:13px; margin-left:8px;">View Website &rarr;</a>
                </div>
            </div>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background:#f8f9fa; padding:20px; color:#202124;">
            <div style="max-width:650px; margin:0 auto;">
                <div style="text-align:center; padding:20px 0;">
                    <h2 style="color:#1a73e8; margin:0;">🔔 Upcoming IT & Tech Conferences</h2>
                    <p style="color:#5f6368; margin-top:4px;">Discovered events matching your interests and region</p>
                </div>
                {rows_html}
                <div style="text-align:center; color:#9aa0a6; font-size:12px; padding:20px 0;">
                    Sent automatically by Tech Conference & Convention Notifier
                </div>
            </div>
        </body>
        </html>
        """

    def notify(self, conferences: List[Conference]) -> bool:
        if not self.sender_email or not self.sender_password or not self.recipient_email or not conferences:
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"🔔 IT & Tech Conferences Alert: {len(conferences)} Upcoming Events"
            msg["From"] = self.sender_email
            msg["To"] = self.recipient_email

            # Plain text fallback
            plain_text = "Upcoming IT & Tech Conferences:\n\n"
            for c in conferences:
                plain_text += f"- {c.name} ({c.formatted_date_range}) in {c.location_str}\n  Link: {c.url}\n\n"

            html_content = self._build_html(conferences)

            msg.attach(MIMEText(plain_text, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=15) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, self.recipient_email, msg.as_string())

            return True
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False

    def test_notification(self) -> bool:
        if not self.sender_email or not self.sender_password or not self.recipient_email:
            return False

        try:
            msg = MIMEText("This is a test notification confirming your Tech Conference Notifier email setup is working!")
            msg["Subject"] = "✅ Tech Conference Notifier: Email Test"
            msg["From"] = self.sender_email
            msg["To"] = self.recipient_email

            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=15) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, self.recipient_email, msg.as_string())

            return True
        except Exception as e:
            logger.error(f"Email test failed: {e}")
            return False
