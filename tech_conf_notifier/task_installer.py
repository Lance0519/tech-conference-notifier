from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from tech_conf_notifier.scheduler import get_local_time_for_manila_time

logger = logging.getLogger("tech_conf_notifier.task_installer")

DEFAULT_TASK_NAME = "TechConfNotifier"


def find_pythonw_executable() -> Path:
    """
    Locates the pythonw.exe binary for silent background execution without console popups.
    Falls back to sys.executable if pythonw.exe cannot be found.
    """
    current_exe = Path(sys.executable)
    pythonw_candidate = current_exe.parent / "pythonw.exe"
    if pythonw_candidate.exists():
        return pythonw_candidate

    which_pythonw = shutil.which("pythonw.exe")
    if which_pythonw:
        return Path(which_pythonw)

    logger.warning("pythonw.exe not found in environment; falling back to current Python interpreter.")
    return current_exe


def find_run_notifier_script() -> Path:
    """
    Locates the absolute path to run_notifier.py in the project directory.
    """
    # Check current directory
    cwd_script = Path.cwd() / "run_notifier.py"
    if cwd_script.exists():
        return cwd_script.resolve()

    # Check parent directory relative to this file
    module_script = Path(__file__).resolve().parent.parent / "run_notifier.py"
    if module_script.exists():
        return module_script.resolve()

    # Fallback to cwd run_notifier.py
    return cwd_script.resolve()


class WindowsTaskScheduler:
    """
    Manages Windows Task Scheduler integration using schtasks.exe.
    Installs and unregisters automated background tasks running under pythonw.exe.
    """

    def __init__(self, task_name: str = DEFAULT_TASK_NAME):
        self.task_name = task_name
        self.pythonw_exe = find_pythonw_executable()
        self.script_path = find_run_notifier_script()

    def install(
        self,
        run_mode: str = "check",
        schedule_type: str = "DAILY",
        start_time_manila: str = "09:00",
        repeat_interval_min: int = 720,  # 720 minutes = 12 hours (dual cadence)
        on_logon: bool = False
    ) -> Dict[str, Any]:
        """
        Registers a silent scheduled task via schtasks.exe.

        :param run_mode: Argument passed to run_notifier.py ('check' or 'daemon')
        :param schedule_type: Schtasks schedule type (DAILY, HOURLY, MINUTE, etc.)
        :param start_time_manila: Target start time in Asia/Manila (converted to local system time)
        :param repeat_interval_min: Interval in minutes to repeat task (720 min = 12h for dual cadence)
        :param on_logon: If True, schedules task to execute at user logon instead of daily timer
        :return: Execution summary dictionary
        """
        if sys.platform != "win32":
            return {
                "success": False,
                "task_name": self.task_name,
                "message": "Windows Task Scheduler integration is only supported on Windows operating systems."
            }

        if not self.script_path.exists():
            return {
                "success": False,
                "task_name": self.task_name,
                "message": f"Target entry script not found: {self.script_path}"
            }

        # Form taskrun command string: "C:\path\pythonw.exe" "C:\path\run_notifier.py" <mode>
        task_run_cmd = f'"{self.pythonw_exe}" "{self.script_path}" {run_mode}'

        cmd = ["schtasks", "/Create", "/TN", self.task_name, "/TR", task_run_cmd, "/F"]

        if on_logon:
            cmd.extend(["/SC", "ONLOGON"])
            cadence_desc = "At user logon"
        else:
            local_time = get_local_time_for_manila_time(start_time_manila)
            cmd.extend(["/SC", schedule_type, "/ST", local_time])

            if repeat_interval_min > 0:
                # Repeat every N minutes for 24 hours daily
                cmd.extend(["/RI", str(repeat_interval_min), "/DU", "24:00"])
                cadence_desc = f"Daily starting at {start_time_manila} Manila ({local_time} Local), repeating every {repeat_interval_min // 60}h"
            else:
                cadence_desc = f"Daily at {start_time_manila} Manila ({local_time} Local)"

        logger.debug(f"Executing schtasks command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            details = self.query()
            return {
                "success": True,
                "task_name": self.task_name,
                "python_executable": str(self.pythonw_exe),
                "script_path": str(self.script_path),
                "run_mode": run_mode,
                "cadence": cadence_desc,
                "command": task_run_cmd,
                "schtasks_output": result.stdout.strip(),
                "task_details": details,
                "message": f"Successfully registered Windows scheduled task '{self.task_name}'."
            }
        else:
            err = result.stderr.strip() or result.stdout.strip()
            return {
                "success": False,
                "task_name": self.task_name,
                "command": task_run_cmd,
                "error": err,
                "message": f"Failed to register Windows scheduled task: {err}"
            }

    def remove(self) -> Dict[str, Any]:
        """
        Unregisters the scheduled task from Windows Task Scheduler.
        """
        if sys.platform != "win32":
            return {
                "success": False,
                "task_name": self.task_name,
                "message": "Windows Task Scheduler integration is only supported on Windows operating systems."
            }

        # Check if task exists first
        if not self.exists():
            return {
                "success": False,
                "task_name": self.task_name,
                "message": f"Task '{self.task_name}' does not exist in Windows Task Scheduler."
            }

        cmd = ["schtasks", "/Delete", "/TN", self.task_name, "/F"]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            return {
                "success": True,
                "task_name": self.task_name,
                "schtasks_output": result.stdout.strip(),
                "message": f"Successfully removed Windows scheduled task '{self.task_name}'."
            }
        else:
            err = result.stderr.strip() or result.stdout.strip()
            return {
                "success": False,
                "task_name": self.task_name,
                "error": err,
                "message": f"Failed to remove scheduled task: {err}"
            }

    def exists(self) -> bool:
        """Returns True if the scheduled task is registered in Windows Task Scheduler."""
        if sys.platform != "win32":
            return False
        cmd = ["schtasks", "/Query", "/TN", self.task_name]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0

    def query(self) -> Optional[Dict[str, str]]:
        """
        Queries and parses task details from Windows Task Scheduler.
        """
        if sys.platform != "win32" or not self.exists():
            return None

        cmd = ["schtasks", "/Query", "/TN", self.task_name, "/FO", "LIST"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            return None

        details: Dict[str, str] = {}
        for line in res.stdout.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                k_clean = key.strip()
                v_clean = val.strip()
                if k_clean and v_clean:
                    details[k_clean] = v_clean
        return details

    def run_now(self) -> Dict[str, Any]:
        """Manually triggers the registered scheduled task immediately."""
        if sys.platform != "win32":
            return {"success": False, "message": "Only supported on Windows."}

        cmd = ["schtasks", "/Run", "/TN", self.task_name]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return {
            "success": res.returncode == 0,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip(),
            "message": "Task triggered successfully." if res.returncode == 0 else f"Failed to run task: {res.stderr.strip()}"
        }
