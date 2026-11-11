from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional

from tech_conf_notifier.config import AppConfig
from tech_conf_notifier.database import Database
from tech_conf_notifier.engine import DiscoveryEngine
from tech_conf_notifier.models import Conference, MANILA_TZ, MANDATORY_CATEGORIES
from tech_conf_notifier.scheduler import ConferenceScheduler, get_local_time_for_manila_time
from tech_conf_notifier.task_installer import WindowsTaskScheduler, DEFAULT_TASK_NAME

logger = logging.getLogger("tech_conf_notifier.cli")


def setup_cli_logging(verbose: bool = False, quiet: bool = False) -> None:
    """Configures console logging levels for CLI runs."""
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )


def format_table(headers: List[str], rows: List[List[str]], max_col_widths: Optional[List[int]] = None) -> str:
    """
    Renders an ASCII tabular representation of data with auto-padding and column limits.
    """
    if not rows:
        return "No matching conferences found."

    num_cols = len(headers)
    widths = [len(h) for h in headers]

    for row in rows:
        for i in range(num_cols):
            cell_len = len(row[i]) if i < len(row) else 0
            if cell_len > widths[i]:
                widths[i] = cell_len

    if max_col_widths:
        for i in range(min(num_cols, len(max_col_widths))):
            if max_col_widths[i] and widths[i] > max_col_widths[i]:
                widths[i] = max_col_widths[i]

    def truncate_cell(val: str, max_w: int) -> str:
        if len(val) <= max_w:
            return val
        return val[: max_w - 3] + "..."

    # Create horizontal border
    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    
    lines = [sep]
    # Header row
    h_cells = [f" {truncate_cell(headers[i], widths[i]).ljust(widths[i])} " for i in range(num_cols)]
    lines.append("|" + "|".join(h_cells) + "|")
    lines.append(sep)

    # Data rows
    for row in rows:
        r_cells = []
        for i in range(num_cols):
            cell_val = row[i] if i < len(row) else ""
            r_cells.append(f" {truncate_cell(cell_val, widths[i]).ljust(widths[i])} ")
        lines.append("|" + "|".join(r_cells) + "|")

    lines.append(sep)
    return "\n".join(lines)


# -----------------------------------------------------------------------------
# CLI Subcommand Implementations
# -----------------------------------------------------------------------------

def cmd_check(args: argparse.Namespace) -> int:
    """Run discovery and notifications once."""
    config = AppConfig.load(args.config) if args.config else AppConfig.load()
    if args.days:
        config.days_lookahead = args.days

    print("\n" + "=" * 72)
    print("  RUNNING CONFERENCE DISCOVERY & NOTIFICATION PIPELINE")
    print("=" * 72)
    print(f"  Lookahead Days:     {config.days_lookahead} days")
    print(f"  Include Academic:   {config.include_academic}")
    print(f"  Config File:        {args.config or 'config.yaml'}")
    print("-" * 72)

    engine = DiscoveryEngine(config=config)
    result = engine.process_and_notify()

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    total_confs = result.get("total_conferences", 0)
    alerts_sent = result.get("alerts_sent", 0)
    dispatches = result.get("dispatches", {})

    print(f"\n  [Pipeline Completed Successfully]")
    print(f"  * Total Active Upcoming Conferences: {total_confs}")
    print(f"  * New / Milestone Alerts Evaluated:  {alerts_sent}")
    print("\n  [Channel Dispatch Status]:")

    channel_labels = {
        "desktop": "Windows Desktop Toasts",
        "discord": "Discord Webhook",
        "telegram": "Telegram Bot",
        "email": "Email (SMTP)",
        "digest": "Local Digest (HTML & Markdown)"
    }

    for ch_name, status in dispatches.items():
        label = channel_labels.get(ch_name, ch_name.title())
        status_str = "SUCCESS" if status else "FAILED / SKIPPED"
        print(f"    - {label:<32}: {status_str}")

    if config.notifiers.digest.enabled:
        html_p = Path(config.notifiers.digest.output_html).resolve()
        md_p = Path(config.notifiers.digest.output_markdown).resolve()
        print(f"\n  [Digest Files Generated]:")
        if html_p.exists():
            print(f"    - HTML Digest:     {html_p}")
        if md_p.exists():
            print(f"    - Markdown Digest: {md_p}")

    print("=" * 72 + "\n")
    return 0


def cmd_daemon(args: argparse.Namespace) -> int:
    """Run continuous background scheduler daemon."""
    config = AppConfig.load(args.config) if args.config else AppConfig.load()
    if args.reminder_time:
        config.schedule.run_at_time = args.reminder_time

    scheduler = ConferenceScheduler(config=config)
    if args.interval:
        scheduler.discovery_interval_hours = args.interval

    run_immediately = not args.no_initial_run

    try:
        scheduler.start_daemon(run_immediately=run_immediately)
    except Exception as e:
        print(f"\n[FATAL] Scheduler daemon error: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_install_task(args: argparse.Namespace) -> int:
    """Register Windows background scheduled task via schtasks.exe."""
    task_name = args.name or DEFAULT_TASK_NAME
    installer = WindowsTaskScheduler(task_name=task_name)

    print("\n" + "=" * 72)
    print("  REGISTERING WINDOWS BACKGROUND SCHEDULED TASK")
    print("=" * 72)
    print(f"  Task Name:          {task_name}")
    print(f"  Execution Target:   {installer.pythonw_exe}")
    print(f"  Script Path:        {installer.script_path}")
    print(f"  Mode:               {args.mode}")

    repeat_min = args.interval * 60 if args.interval else 720  # default 12 hours = 720 min

    res = installer.install(
        run_mode=args.mode,
        schedule_type=args.schedule_type,
        start_time_manila=args.time,
        repeat_interval_min=repeat_min,
        on_logon=args.on_logon
    )

    if res.get("success"):
        print(f"  Cadence:            {res.get('cadence')}")
        print(f"  Status:             REGISTERED SUCCESSFULLY")
        print("-" * 72)
        print("  Windows Task Details:")
        details = res.get("task_details") or {}
        if details:
            for k, v in details.items():
                print(f"    {k:<18}: {v}")
        else:
            print(f"    {res.get('message')}")
        print("=" * 72 + "\n")
        return 0
    else:
        print(f"  Status:             FAILED")
        print(f"  Error:              {res.get('error') or res.get('message')}")
        print("=" * 72 + "\n")
        return 1


def cmd_remove_task(args: argparse.Namespace) -> int:
    """Unregister Windows background scheduled task."""
    task_name = args.name or DEFAULT_TASK_NAME
    installer = WindowsTaskScheduler(task_name=task_name)

    print("\n" + "=" * 72)
    print("  UNREGISTERING WINDOWS BACKGROUND SCHEDULED TASK")
    print("=" * 72)
    print(f"  Task Name: {task_name}")

    res = installer.remove()
    if res.get("success"):
        print(f"  Status:    REMOVED SUCCESSFULLY")
        print(f"  Details:   {res.get('message')}")
    else:
        print(f"  Status:    NOT FOUND OR REMOVAL FAILED")
        print(f"  Details:   {res.get('message')}")
    print("=" * 72 + "\n")
    return 0 if res.get("success") else 1


def cmd_test_notifiers(args: argparse.Namespace) -> int:
    """Test configured notification channels."""
    config = AppConfig.load(args.config) if args.config else AppConfig.load()
    engine = DiscoveryEngine(config=config)

    print("\n" + "=" * 72)
    print("  TESTING NOTIFICATION CHANNELS")
    print("=" * 72)

    selected_channel = (args.channel or "all").lower()
    headers = ["Channel", "Status in Config", "Test Result", "Details / Note"]
    table_rows = []

    # Map of all possible notifiers
    channels_to_test = []
    for notif in engine.notifiers:
        if selected_channel in ("all", notif.name):
            channels_to_test.append(notif)

    all_channels_status = {
        "desktop": config.notifiers.desktop.enabled,
        "discord": config.notifiers.discord.enabled,
        "telegram": config.notifiers.telegram.enabled,
        "email": config.notifiers.email.enabled,
        "digest": config.notifiers.digest.enabled,
    }

    active_names = {n.name for n in channels_to_test}

    # Test active channels
    for notif in channels_to_test:
        enabled_str = "Enabled"
        try:
            print(f"  Testing channel: {notif.name}...")
            ok = notif.test_notification()
            result_str = "PASS (OK)" if ok else "FAIL"
            note = "Test alert sent successfully" if ok else "Check channel credentials/network"
            if notif.name == "desktop":
                note = "Native Windows toast displayed"
            elif notif.name == "digest":
                note = "Generated sample HTML & Markdown digest"
        except Exception as e:
            result_str = "ERROR"
            note = str(e)[:40]

        table_rows.append([notif.name.title(), enabled_str, result_str, note])

    # Show disabled channels if 'all' was selected
    if selected_channel == "all":
        for ch_name, is_enabled in all_channels_status.items():
            if ch_name not in active_names:
                table_rows.append([
                    ch_name.title(),
                    "Disabled",
                    "SKIPPED",
                    "Enable in config.yaml to activate"
                ])

    print("\n" + format_table(headers, table_rows, [12, 18, 14, 40]))
    print("=" * 72 + "\n")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    """Launch mobile REST API & Web PWA server on port 5000."""
    from tech_conf_notifier.api import start_server
    start_server(host=args.host, port=args.port, debug=args.debug)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """Display upcoming conferences in formatted CLI table."""
    config = AppConfig.load(args.config) if args.config else AppConfig.load()
    db = Database.get_instance()

    days = args.days or config.days_lookahead
    category = args.category
    format_filter = args.format
    country = "Philippines" if args.ph_only else args.country
    search = args.search
    limit = args.limit or 30

    events = db.get_upcoming_events(
        days_lookahead=days,
        category=category,
        format_filter=format_filter,
        country=country,
        search_query=search
    )

    if not events:
        # Check if database has any events at all
        all_events = db.get_upcoming_events(days_lookahead=365)
        if not all_events:
            print("\nDatabase is currently empty. Running an initial discovery pass...")
            engine = DiscoveryEngine(config=config)
            events = engine.run_discovery()
            # Re-apply filters
            events = db.get_upcoming_events(
                days_lookahead=days,
                category=category,
                format_filter=format_filter,
                country=country,
                search_query=search
            )

    print("\n" + "=" * 90)
    print("  UPCOMING TECH & IT CONFERENCES & CONVENTIONS")
    print("=" * 90)
    filter_desc = []
    if category:
        filter_desc.append(f"Category: {category}")
    if format_filter and format_filter != "all":
        filter_desc.append(f"Format: {format_filter}")
    if country:
        filter_desc.append(f"Country: {country}")
    if search:
        filter_desc.append(f"Search: '{search}'")
    filter_desc.append(f"Lookahead: {days} days")

    print("  Filters: " + " | ".join(filter_desc))
    print(f"  Showing: {min(len(events), limit)} of {len(events)} matching conferences")
    print("-" * 90)

    headers = [
        "Date",
        "D-Day",
        "Event Name",
        "Category",
        "Format",
        "Location",
        "CFP Due"
    ]

    rows = []
    for conf in events[:limit]:
        d_day_str = f"{conf.days_until}d" if conf.days_until >= 0 else f"{conf.days_until}d (past)"
        if conf.days_until == 0:
            d_day_str = "TODAY"
        elif conf.days_until == 1:
            d_day_str = "1d (tmrw)"

        cfp_str = "-"
        if conf.cfp_deadline:
            days_cfp = (conf.cfp_deadline - date.today()).days
            cfp_str = f"{conf.cfp_deadline.strftime('%b %d')} ({days_cfp}d)" if days_cfp >= 0 else "Closed"

        flag = " [PH]" if conf.is_philippines else ""
        name_display = f"{conf.name}{flag}"

        rows.append([
            conf.start_date.strftime("%Y-%m-%d"),
            d_day_str,
            name_display,
            conf.category,
            conf.format.capitalize(),
            conf.location_str,
            cfp_str
        ])

    max_col_widths = [12, 10, 32, 22, 10, 24, 16]
    print(format_table(headers, rows, max_col_widths))

    ph_count = sum(1 for e in events if e.is_philippines)
    online_count = sum(1 for e in events if e.is_online)
    cfp_count = sum(1 for e in events if e.has_cfp_open)
    student_count = sum(1 for e in events if e.is_student_friendly or "Students" in e.target_audiences)

    print(f"\n  Summary: {len(events)} total conferences | {student_count} Student-Friendly 🎓 | "
          f"{ph_count} Philippines [PH] | {online_count} Online/Hybrid | {cfp_count} Open CFP")
    print("=" * 90 + "\n")
    return 0


def cmd_verify_urls(args: argparse.Namespace) -> int:
    """Actively test and verify all conference websites and registration URLs."""
    config = AppConfig.load(args.config) if args.config else AppConfig.load()
    engine = DiscoveryEngine(config=config)

    print("\n" + "=" * 80)
    print("  CHECKING LEGITIMACY & REACHABILITY OF ALL CONFERENCE SITES & URLS")
    print("=" * 80)
    print(f"  Timeout: {args.timeout}s | User-Agent: Chrome / Windows Browser Header")
    print("-" * 80)

    results = engine.verify_all_urls(timeout=args.timeout)

    print(f"\n  [URL Verification Results]")
    print(f"  * Total Evaluated Conferences:       {results['total']}")
    print(f"  * Reachable & Live URLs [200 OK]:    {results['verified']}")
    print(f"  * Unreachable / Dead Links Excluded: {results['dead']}")
    print("-" * 80)

    if args.verbose or args.show_details:
        print("\n  [Detailed Link Audit]:")
        for item in results["details"]:
            status_indicator = "[LIVE]" if item["status"] == "ok" else "[DEAD]"
            code_str = f"HTTP {item['code']}" if item["code"] else "NO_RESPONSE"
            name_snip = item["name"][:35]
            print(f"    {status_indicator:<7} {code_str:<15} {name_snip:<35} -> {item['url']}")

    print("\n  Summary: Dead links are flagged as 'dead_link' and automatically")
    print("  excluded from all user feeds, digests, and notification channels.")
    print("=" * 80 + "\n")
    return 0


# -----------------------------------------------------------------------------
# Main Parser Construction
# -----------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Builds the unified CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="py run_notifier.py",
        description="IT & Tech Conference Automated Notifier System CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  py run_notifier.py check                Run discovery and dispatch notifications
  py run_notifier.py list --ph-only       Display upcoming Philippine tech conferences
  py run_notifier.py daemon               Start the continuous dual-cadence scheduler daemon
  py run_notifier.py install-task         Register silent Windows scheduled task (pythonw.exe)
  py run_notifier.py remove-task          Unregister Windows scheduled task
  py run_notifier.py test-notifiers       Test configured notification channels (toasts, email, etc.)
  py run_notifier.py serve --port 5000    Launch mobile REST API & Web PWA server
        """
    )

    parser.add_argument("--config", "-c", type=str, default=None, help="Path to config.yaml")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose DEBUG logging")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress non-error logs")

    subparsers = parser.add_subparsers(dest="command", title="Commands", metavar="<command>")

    # Command: check (with sync alias)
    p_check = subparsers.add_parser("check", aliases=["sync"], help="Run discovery & notifications once")
    p_check.add_argument("--days", "-d", type=int, default=None, help="Lookahead window in days")
    p_check.add_argument("--json", action="store_true", help="Output summary in JSON format")

    # Command: daemon
    p_daemon = subparsers.add_parser("daemon", help="Run continuous background scheduler")
    p_daemon.add_argument("--no-initial-run", action="store_true", help="Skip immediate check upon startup")
    p_daemon.add_argument("--interval", "-i", type=int, default=12, help="Discovery cycle interval in hours (default: 12)")
    p_daemon.add_argument("--reminder-time", "-t", type=str, default="09:00", help="Daily reminder time in Asia/Manila (default: '09:00')")

    # Command: install-task
    p_install = subparsers.add_parser("install-task", help="Register Windows background scheduled task (via schtasks.exe)")
    p_install.add_argument("--name", "-n", type=str, default=DEFAULT_TASK_NAME, help=f"Task name (default: '{DEFAULT_TASK_NAME}')")
    p_install.add_argument("--mode", "-m", choices=["check", "daemon"], default="check", help="Target mode to execute ('check' or 'daemon', default: 'check')")
    p_install.add_argument("--schedule-type", choices=["DAILY", "HOURLY", "WEEKLY"], default="DAILY", help="Schedule frequency (default: DAILY)")
    p_install.add_argument("--time", "-t", type=str, default="09:00", help="Start time in Asia/Manila (default: '09:00')")
    p_install.add_argument("--interval", "-i", type=int, default=12, help="Repetition interval in hours (default: 12)")
    p_install.add_argument("--on-logon", action="store_true", help="Trigger at user logon instead of timer")

    # Command: remove-task
    p_remove = subparsers.add_parser("remove-task", help="Unregister Windows background scheduled task")
    p_remove.add_argument("--name", "-n", type=str, default=DEFAULT_TASK_NAME, help=f"Task name (default: '{DEFAULT_TASK_NAME}')")

    # Command: test-notifiers
    p_test = subparsers.add_parser("test-notifiers", help="Test active/configured notification channels")
    p_test.add_argument("--channel", "-C", type=str, choices=["all", "desktop", "discord", "telegram", "email", "digest"], default="all", help="Specific channel to test (default: all)")

    # Command: serve
    p_serve = subparsers.add_parser("serve", help="Launch mobile REST API & Web PWA server on port 5000")
    p_serve.add_argument("--host", type=str, default="0.0.0.0", help="Host address to bind (default: '0.0.0.0')")
    p_serve.add_argument("--port", "-p", type=int, default=5000, help="Port to listen on (default: 5000)")
    p_serve.add_argument("--debug", action="store_true", help="Run Flask in debug mode")

    # Command: list
    p_list = subparsers.add_parser("list", help="Display upcoming conferences in formatted CLI table")
    p_list.add_argument("--days", "-d", type=int, default=60, help="Lookahead window in days (default: 60)")
    p_list.add_argument("--category", "-C", type=str, default=None, help="Filter by IT/CS category")
    p_list.add_argument("--format", "-f", type=str, choices=["all", "in_person", "virtual", "hybrid"], default="all", help="Filter by format")
    p_list.add_argument("--country", type=str, default=None, help="Filter by country")
    p_list.add_argument("--ph-only", action="store_true", help="Shortcut to show only Philippine conferences")
    p_list.add_argument("--search", "-s", type=str, default=None, help="Search query string")
    p_list.add_argument("--limit", "-l", type=int, default=25, help="Maximum number of rows to display (default: 25)")

    # Command: verify-urls
    p_verify = subparsers.add_parser("verify-urls", help="Verify that all conference websites and registration links are legitimate and openable")
    p_verify.add_argument("--timeout", "-t", type=int, default=6, help="Request timeout in seconds (default: 6)")
    p_verify.add_argument("--show-details", "-d", action="store_true", help="Print status of each URL")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI execution entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    setup_cli_logging(verbose=args.verbose, quiet=args.quiet)

    if not args.command:
        parser.print_help()
        return 0

    commands_map = {
        "check": cmd_check,
        "sync": cmd_check,
        "daemon": cmd_daemon,
        "install-task": cmd_install_task,
        "remove-task": cmd_remove_task,
        "test-notifiers": cmd_test_notifiers,
        "serve": cmd_serve,
        "list": cmd_list,
        "verify-urls": cmd_verify_urls
    }

    handler = commands_map.get(args.command)
    if not handler:
        parser.print_help()
        return 1

    return handler(args)
