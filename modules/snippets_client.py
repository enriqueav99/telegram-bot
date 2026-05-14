"""Almacenamiento persistente de snippets de texto/código."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

SNIPPETS_FILE = Path("data/snippets.json")


def _load() -> dict[str, dict]:
    if not SNIPPETS_FILE.exists():
        return {}
    return json.loads(SNIPPETS_FILE.read_text())


def _save(snippets: dict[str, dict]) -> None:
    SNIPPETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SNIPPETS_FILE.write_text(json.dumps(snippets, indent=2))


def add(name: str, content: str) -> None:
    snippets = _load()
    snippets[name] = {"content": content, "created_at": datetime.now(UTC).isoformat()}
    _save(snippets)


def get(name: str) -> str | None:
    entry = _load().get(name)
    return entry["content"] if entry else None


def list_all() -> dict[str, dict]:
    return _load()


def delete(name: str) -> bool:
    snippets = _load()
    if name not in snippets:
        return False
    del snippets[name]
    _save(snippets)
    return True
