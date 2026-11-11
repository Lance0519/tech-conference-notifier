from __future__ import annotations

import logging
import signal
import sys
import time
from datetime import datetime
import schedule

from tech_conf_notifier.config import AppConfig
from tech_conf_notifier.engine import DiscoveryEngine
from tech_conf_notifier.models import MANILA_TZ

logger = logging.getLogger("tech_conf_notifier.daemon")

running = True


def _signal_handler(signum, frame):
    global running
    print("\n[DAEMON] Shutting down autonomous background scheduler daemon...")
    running = False


def run_sync_job(engine: DiscoveryEngine):
    """Executes a single scheduled discovery & notification run."""
    now_str = datetime.now(MANILA_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")
    logger.info(f"Triggering scheduled discovery job at {now_str}...")
    try:
        result = engine.process_and_notify()
        logger.info(
            f"Scheduled job completed. Discovered: {result['total_conferences']}, Alerts: {result['alerts_sent']}"
        )
    except Exception as e:
        logger.error(f"Error executing scheduled job: {e}", exc_info=True)


def run_daemon():
    """Runs the continuous scheduler loop."""
    global running
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    signal.signal(signal.SIGINT, _signal_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _signal_handler)

    config = AppConfig.load()
    engine = DiscoveryEngine(config=config)

    print("=" * 68)
    print("  TECH CONFERENCES & CONVENTIONS NOTIFIER - BACKGROUND DAEMON")
    print("=" * 68)
    print(f"  Timezone Anchor : Manila (Asia/Manila UTC+8)")
    print(f"  Daily Schedule  : Every day at {config.schedule.run_at_time}")
    print(f"  Interval Fallback: Every {config.schedule.interval_hours} hours")
    print("=" * 68)

    # 1. Immediate initial run on startup
    print("\n[DAEMON] Executing initial synchronization on startup...")
    run_sync_job(engine)

    # 2. Configure recurring schedule
    run_time = config.schedule.run_at_time or "09:00"
    schedule.every().day.at(run_time).do(run_sync_job, engine=engine)

    if config.schedule.interval_hours and config.schedule.interval_hours < 24:
        schedule.every(config.schedule.interval_hours).hours.do(run_sync_job, engine=engine)

    print(f"\n[DAEMON] Scheduler initialized. Next job scheduled at {schedule.next_run()}")
    print("[DAEMON] Press Ctrl+C to terminate the daemon safely.\n")

    while running:
        schedule.run_pending()
        time.sleep(1)

    print("[DAEMON] Autonomous daemon stopped cleanly.")


if __name__ == "__main__":
    run_daemon()
