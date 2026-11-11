#!/usr/bin/env python3
"""
IT & Tech Conference Automated Notifier System
===============================================
Unified entrypoint script for CLI operations, scheduler daemon,
Windows Task Scheduler integration, mobile REST API / Web PWA server,
and on-demand discovery checks.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tech_conf_notifier.cli import main

if __name__ == "__main__":
    sys.exit(main())
