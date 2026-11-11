from __future__ import annotations

import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from zoneinfo import ZoneInfo

import schedule

from tech_conf_notifier.config import AppConfig
from tech_conf_notifier.engine import DiscoveryEngine
from tech_conf_notifier.models import MANILA_TZ

logger = logging.getLogger("tech_conf_notifier.scheduler")


class SchedulerLockError(RuntimeError):
    """Raised when another scheduler daemon instance is already active."""
    pass


class SchedulerLock:
    """
    Ensures single-instance daemon execution using an OS-level file lock
    on .cache/scheduler.lock.
    """

    def __init__(self, lock_file: str | Path = ".cache/scheduler.lock"):
        self.lock_path = Path(lock_file).resolve()
        self._file_handle = None
        self._is_locked = False

    def acquire(self) -> bool:
        """
        Attempts to acquire an exclusive non-blocking lock.
        Returns True if acquired, raises SchedulerLockError if already held.
        """
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Open with 'a+' so existing file can be checked/read before locking
            self._file_handle = open(self.lock_path, "a+", encoding="utf-8")
            self._file_handle.seek(0)

            if sys.platform == "win32":
                import msvcrt
                try:
                    msvcrt.locking(self._file_handle.fileno(), msvcrt.LK_NBLCK, 1)
                except (OSError, PermissionError) as e:
                    existing_pid = self._read_existing_pid()
                    self._file_handle.close()
                    self._file_handle = None
                    raise SchedulerLockError(
                        f"Another scheduler daemon instance is already running (PID: {existing_pid or 'unknown'}). "
                        f"Lock file: {self.lock_path}"
                    ) from e
            else:
                import fcntl
                try:
                    fcntl.flock(self._file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except (IOError, OSError) as e:
                    existing_pid = self._read_existing_pid()
                    self._file_handle.close()
                    self._file_handle = None
                    raise SchedulerLockError(
                        f"Another scheduler daemon instance is already running (PID: {existing_pid or 'unknown'}). "
                        f"Lock file: {self.lock_path}"
                    ) from e

            # Write current instance info
            self._file_handle.seek(0)
            self._file_handle.truncate()
            payload = (
                f"PID={os.getpid()}\n"
                f"STARTED_AT={datetime.now().isoformat()}\n"
                f"TIMEZONE=Asia/Manila\n"
            )
            self._file_handle.write(payload)
            self._file_handle.flush()
            self._is_locked = True
            logger.debug(f"Scheduler lock acquired by PID {os.getpid()} on {self.lock_path}")
            return True

        except SchedulerLockError:
            raise
        except Exception as e:
            if self._file_handle:
                try:
                    self._file_handle.close()
                except Exception:
                    pass
                self._file_handle = None
            raise SchedulerLockError(f"Failed to acquire scheduler lock: {e}") from e

    def release(self) -> None:
        """Releases the lock and removes the lock file."""
        if not self._is_locked or not self._file_handle:
            return

        try:
            self._file_handle.seek(0)
            if sys.platform == "win32":
                import msvcrt
                try:
                    msvcrt.locking(self._file_handle.fileno(), msvcrt.LK_UNLCK, 1)
                except Exception:
                    pass
            else:
                import fcntl
                try:
                    fcntl.flock(self._file_handle.fileno(), fcntl.LOCK_UN)
                except Exception:
                    pass

            self._file_handle.close()
            self._file_handle = None
            self._is_locked = False

            if self.lock_path.exists():
                try:
                    self.lock_path.unlink()
                except OSError:
                    pass
            logger.debug("Scheduler lock released successfully.")
        except Exception as e:
            logger.warning(f"Error while releasing lock: {e}")

    def _read_existing_pid(self) -> Optional[int]:
        """Attempt to read the PID from the existing lock file."""
        try:
            self._file_handle.seek(0)
            for line in self._file_handle:
                if line.startswith("PID="):
                    return int(line.strip().split("=")[1])
        except Exception:
            pass
        return None

    def is_locked(self) -> bool:
        """Returns True if the lock is held by any active process."""
        if not self.lock_path.exists():
            return False
        try:
            with open(self.lock_path, "r", encoding="utf-8") as f:
                content = f.read()
                pid = None
                for line in content.splitlines():
                    if line.startswith("PID="):
                        pid = int(line.split("=")[1])
                        break
            if pid and sys.platform == "win32":
                import ctypes
                h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
                if h:
                    ctypes.windll.kernel32.CloseHandle(h)
                    return True
                return False
            elif pid:
                os.kill(pid, 0)
                return True
        except Exception:
            pass
        return False

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


def get_local_time_for_manila_time(manila_time_str: str = "09:00") -> str:
    """
    Converts a 24-hour time string in Asia/Manila (e.g. '09:00') into
    the equivalent local machine time string 'HH:MM'.
    """
    try:
        parts = manila_time_str.strip().split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0

        now_manila = datetime.now(MANILA_TZ)
        target_manila = now_manila.replace(hour=hour, minute=minute, second=0, microsecond=0)
        local_target = target_manila.astimezone()
        return local_target.strftime("%H:%M")
    except Exception as e:
        logger.warning(f"Failed to convert Manila time '{manila_time_str}': {e}. Falling back to '09:00'.")
        return "09:00"


class ConferenceScheduler:
    """
    Background scheduler orchestrating dual-cadence cycles:
    1. 12-hour Discovery Cycle: Multi-source feed fetch, deduplication, and database cache refresh.
    2. 24-hour Recheck & Milestone Reminder Cycle: Executed daily at 09:00 Asia/Manila to evaluate
       milestones (starts today, 1d, 3d, 7d; CFP 1d, 3d, 7d, 14d) and compile daily digests.
    """

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        engine: Optional[DiscoveryEngine] = None,
        lock_file: str = ".cache/scheduler.lock"
    ):
        self.config = config or AppConfig.load()
        self.engine = engine or DiscoveryEngine(self.config)
        self.lock = SchedulerLock(lock_file)
        self.scheduler = schedule.Scheduler()
        self._stop_requested = False
        self.discovery_interval_hours = 12
        self.manila_reminder_time = self.config.schedule.run_at_time or "09:00"

    def run_discovery_cycle(self) -> Dict[str, Any]:
        """
        Executes the 12-hour discovery cycle. Fetches feeds, sanitizes, deduplicates,
        and persists newly discovered events into SQLite.
        """
        logger.info("=== [12-Hour Cadence] Starting Conference Discovery Cycle ===")
        start_t = time.time()
        try:
            conferences = self.engine.run_discovery()
            elapsed = time.time() - start_t
            logger.info(
                f"=== [12-Hour Cadence] Discovery completed in {elapsed:.2f}s. "
                f"Active upcoming conferences: {len(conferences)} ==="
            )
            return {
                "cycle": "discovery_12h",
                "timestamp": datetime.now(MANILA_TZ).isoformat(),
                "total_conferences": len(conferences),
                "duration_seconds": round(elapsed, 2)
            }
        except Exception as e:
            logger.error(f"Error during 12-hour discovery cycle: {e}", exc_info=True)
            return {"cycle": "discovery_12h", "error": str(e)}

    def run_daily_reminder_cycle(self) -> Dict[str, Any]:
        """
        Executes the 24-hour milestone reminder and digest generation cycle.
        Triggered daily at 09:00 Asia/Manila.
        """
        logger.info("=== [24-Hour Cadence] Starting Daily 09:00 Manila Milestone & Digest Cycle ===")
        start_t = time.time()
        try:
            result = self.engine.process_and_notify()
            elapsed = time.time() - start_t
            logger.info(
                f"=== [24-Hour Cadence] Daily cycle completed in {elapsed:.2f}s. "
                f"Alerts dispatched: {result.get('alerts_sent', 0)} ==="
            )
            return {
                "cycle": "reminder_24h_0900",
                "timestamp": datetime.now(MANILA_TZ).isoformat(),
                "duration_seconds": round(elapsed, 2),
                **result
            }
        except Exception as e:
            logger.error(f"Error during daily reminder cycle: {e}", exc_info=True)
            return {"cycle": "reminder_24h_0900", "error": str(e)}

    def run_once(self) -> Dict[str, Any]:
        """Runs an immediate on-demand discovery and notification pass."""
        logger.info("Executing immediate on-demand conference check...")
        return self.engine.process_and_notify()

    def setup_jobs(self) -> None:
        """Configures the dual-cadence scheduled jobs on the scheduler."""
        self.scheduler.clear()

        # Job 1: 12-Hour Discovery Cycle
        self.scheduler.every(self.discovery_interval_hours).hours.do(self.run_discovery_cycle)

        # Job 2: 24-Hour Daily Reminder at 09:00 Asia/Manila
        local_time_str = get_local_time_for_manila_time(self.manila_reminder_time)
        self.scheduler.every().day.at(local_time_str).do(self.run_daily_reminder_cycle)

        logger.info(
            f"Scheduler jobs configured:\n"
            f"  - 12-Hour Discovery: Every {self.discovery_interval_hours} hours\n"
            f"  - 24-Hour Milestones & Digest: Daily at {self.manila_reminder_time} Manila time "
            f"(Local machine time: {local_time_str})"
        )

    def print_schedule_summary(self) -> None:
        """Displays next execution timestamps for active jobs."""
        local_reminder_time = get_local_time_for_manila_time(self.manila_reminder_time)
        print("=" * 70)
        print("  TECH CONFERENCE NOTIFIER - BACKGROUND SCHEDULER DAEMON")
        print("=" * 70)
        print(f"  PID:                 {os.getpid()}")
        print(f"  Lock File:           {self.lock.lock_path}")
        print(f"  Cadence 1:           12-Hour Discovery Cycle (every {self.discovery_interval_hours}h)")
        print(f"  Cadence 2:           24-Hour Milestone & Digest Cycle (Daily at {self.manila_reminder_time} Manila / {local_reminder_time} Local)")
        
        for idx, job in enumerate(self.scheduler.jobs, start=1):
            next_t = job.next_run.strftime('%Y-%m-%d %H:%M:%S') if job.next_run else 'Pending'
            print(f"  Scheduled Job #{idx}:  Next run at {next_t} ({job.job_func.__name__})")
        print("=" * 70)
        print("  Press Ctrl+C to gracefully stop the scheduler daemon.\n")

    def start_daemon(self, run_immediately: bool = True) -> None:
        """
        Starts the in-process daemon loop under single-instance lock.
        Blocks until SIGINT/SIGTERM is received.
        """
        # Ensure single-instance lock
        self.lock.acquire()

        # Wire graceful shutdown handlers
        def _handle_exit(sig, frame):
            logger.info(f"Signal {sig} received. Initiating graceful shutdown...")
            self.stop()

        try:
            signal.signal(signal.SIGINT, _handle_exit)
            signal.signal(signal.SIGTERM, _handle_exit)
        except (ValueError, AttributeError):
            # Non-main thread or unsupported platform
            pass

        try:
            self.setup_jobs()

            if run_immediately:
                logger.info("Executing initial startup discovery & notification pass...")
                self.run_daily_reminder_cycle()

            self.print_schedule_summary()

            while not self._stop_requested:
                self.scheduler.run_pending()
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt caught. Stopping scheduler daemon...")
        finally:
            self.lock.release()
            logger.info("Scheduler daemon terminated cleanly.")

    def stop(self) -> None:
        """Requests graceful termination of the daemon loop."""
        self._stop_requested = True
