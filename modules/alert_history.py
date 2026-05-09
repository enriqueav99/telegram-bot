"""Persistent store for recent webhook alerts."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

HISTORY_FILE = Path("data/alert_history.json")
MAX_ALERTS = 50


def _load() -> list[dict]:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except Exception:
            return []
    return []


def _save(alerts: list[dict]) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(alerts, indent=2, ensure_ascii=False))


def record(source: str, name: str, status: str, summary: str) -> None:
    alerts = _load()
    alerts.append({
        "ts": datetime.now(UTC).isoformat(),
        "source": source,
        "name": name,
        "status": status,
        "summary": summary,
    })
    _save(alerts[-MAX_ALERTS:])


def recent(n: int = 15) -> list[dict]:
    return _load()[-n:]


def clear() -> None:
    _save([])
