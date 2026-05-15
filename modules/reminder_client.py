"""Almacenamiento persistente de recordatorios."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

REMINDERS_FILE = Path("data/reminders.json")


def _load() -> list[dict]:
    if not REMINDERS_FILE.exists():
        return []
    return json.loads(REMINDERS_FILE.read_text())


def _save(reminders: list[dict]) -> None:
    REMINDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    REMINDERS_FILE.write_text(json.dumps(reminders, indent=2))


def add(chat_id: int, text: str, fire_at: datetime) -> int:
    reminders = _load()
    next_id = max((r["id"] for r in reminders), default=0) + 1
    reminders.append(
        {
            "id": next_id,
            "chat_id": chat_id,
            "text": text,
            "fire_at": fire_at.isoformat(),
            "done": False,
        }
    )
    _save(reminders)
    return next_id


def list_pending(chat_id: int) -> list[dict]:
    return [r for r in _load() if not r["done"] and r["chat_id"] == chat_id]


def list_all_pending() -> list[dict]:
    return [r for r in _load() if not r["done"]]


def mark_done(reminder_id: int) -> None:
    reminders = _load()
    for r in reminders:
        if r["id"] == reminder_id:
            r["done"] = True
    _save(reminders)


def delete(reminder_id: int, chat_id: int) -> bool:
    reminders = _load()
    new = [r for r in reminders if not (r["id"] == reminder_id and r["chat_id"] == chat_id)]
    if len(new) == len(reminders):
        return False
    _save(new)
    return True
