"""Healthcheck: falla si el heartbeat tiene más de 90 segundos de antigüedad."""
from __future__ import annotations

import sys
import time
from pathlib import Path

HEARTBEAT_FILE = Path("/tmp/.bot_alive")
MAX_AGE = 90

if not HEARTBEAT_FILE.exists():
    sys.exit(1)

age = time.time() - float(HEARTBEAT_FILE.read_text())
sys.exit(0 if age < MAX_AGE else 1)
