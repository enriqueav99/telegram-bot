"""Almacenamiento y parsing de comandos programados (cron)."""

from __future__ import annotations

import json
import re
from pathlib import Path

CRON_FILE = Path("data/cron_jobs.json")

_DAILY_RE = re.compile(r"^(\d{1,2}):(\d{2})$")
_MINUTES_RE = re.compile(r"^(\d+)m$")
_HOURS_RE = re.compile(r"^(\d+)h$")


def parse_schedule(schedule: str) -> dict | None:
    """
    Returns {"type": "daily", "hour": int, "minute": int}
         or {"type": "interval", "seconds": int}
         or None if invalid.

    Accepted formats:
      HH:MM  — run daily at that UTC time
      Xm     — run every X minutes (min 5)
      Xh     — run every X hours (max 168)
    """
    m = _DAILY_RE.match(schedule)
    if m:
        h, minute = int(m.group(1)), int(m.group(2))
        if 0 <= h < 24 and 0 <= minute < 60:
            return {"type": "daily", "hour": h, "minute": minute}

    m = _MINUTES_RE.match(schedule)
    if m:
        minutes = int(m.group(1))
        if minutes >= 5:
            return {"type": "interval", "seconds": minutes * 60}

    m = _HOURS_RE.match(schedule)
    if m:
        hours = int(m.group(1))
        if 1 <= hours <= 168:
            return {"type": "interval", "seconds": hours * 3600}

    return None


def _load() -> list[dict]:
    if not CRON_FILE.exists():
        return []
    return json.loads(CRON_FILE.read_text())


def _save(jobs: list[dict]) -> None:
    CRON_FILE.parent.mkdir(parents=True, exist_ok=True)
    CRON_FILE.write_text(json.dumps(jobs, indent=2))


def add(alias: str, schedule: str, chat_id: int) -> int:
    jobs = _load()
    next_id = max((j["id"] for j in jobs), default=0) + 1
    jobs.append({"id": next_id, "alias": alias, "schedule": schedule, "chat_id": chat_id})
    _save(jobs)
    return next_id


def list_all() -> list[dict]:
    return _load()


def delete(job_id: int) -> bool:
    jobs = _load()
    new = [j for j in jobs if j["id"] != job_id]
    if len(new) == len(jobs):
        return False
    _save(new)
    return True
