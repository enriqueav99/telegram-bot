from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

NOTES_FILE = Path("data/notes.json")


def _load() -> list[dict]:
    if not NOTES_FILE.exists():
        return []
    return json.loads(NOTES_FILE.read_text())


def _save(notes: list[dict]) -> None:
    NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
    NOTES_FILE.write_text(json.dumps(notes, indent=2))


def add(text: str) -> int:
    notes = _load()
    next_id = max((n["id"] for n in notes), default=0) + 1
    notes.append({"id": next_id, "text": text, "ts": datetime.now(UTC).isoformat()})
    _save(notes)
    return next_id


def list_all() -> list[dict]:
    return _load()


def delete(note_id: int) -> bool:
    notes = _load()
    new_notes = [n for n in notes if n["id"] != note_id]
    if len(new_notes) == len(notes):
        return False
    _save(new_notes)
    return True
