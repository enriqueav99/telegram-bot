"""Almacenamiento persistente de la lista de tareas."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

TODO_FILE = Path("data/todos.json")


def _load() -> list[dict]:
    if not TODO_FILE.exists():
        return []
    return json.loads(TODO_FILE.read_text())


def _save(todos: list[dict]) -> None:
    TODO_FILE.parent.mkdir(parents=True, exist_ok=True)
    TODO_FILE.write_text(json.dumps(todos, indent=2))


def add(text: str) -> int:
    todos = _load()
    next_id = max((t["id"] for t in todos), default=0) + 1
    todos.append(
        {
            "id": next_id,
            "text": text,
            "done": False,
            "created_at": datetime.now(UTC).isoformat(),
        }
    )
    _save(todos)
    return next_id


def list_all() -> list[dict]:
    return _load()


def mark_done(todo_id: int) -> bool:
    todos = _load()
    for t in todos:
        if t["id"] == todo_id:
            t["done"] = True
            _save(todos)
            return True
    return False


def delete(todo_id: int) -> bool:
    todos = _load()
    new = [t for t in todos if t["id"] != todo_id]
    if len(new) == len(todos):
        return False
    _save(new)
    return True
