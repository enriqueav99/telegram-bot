"""Persistent storage for system alert thresholds."""

from __future__ import annotations

import json
from pathlib import Path

SYSALERTS_FILE = Path("data/sysalerts.json")
METRICS = ("cpu", "ram", "disk")

_DEFAULT_THRESHOLDS: dict[str, float | None] = {
    "cpu": 85.0,
    "ram": 90.0,
    "disk": 85.0,
}


class SysAlertClient:
    def __init__(self) -> None:
        self._thresholds: dict[str, float | None] = dict(_DEFAULT_THRESHOLDS)
        self._firing: set[str] = set()
        self._load()

    def _load(self) -> None:
        if SYSALERTS_FILE.exists():
            saved = json.loads(SYSALERTS_FILE.read_text())
            for k in METRICS:
                if k in saved:
                    v = saved[k]
                    self._thresholds[k] = float(v) if v is not None else None

    def _save(self) -> None:
        SYSALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SYSALERTS_FILE.write_text(json.dumps(self._thresholds, indent=2))

    def get_threshold(self, metric: str) -> float | None:
        return self._thresholds.get(metric)

    def set_threshold(self, metric: str, value: float | None) -> None:
        if metric not in METRICS:
            raise ValueError(f"Métrica desconocida: {metric}")
        self._thresholds[metric] = value
        self._save()

    def is_firing(self, metric: str) -> bool:
        return metric in self._firing

    def set_firing(self, metric: str, state: bool) -> None:
        if state:
            self._firing.add(metric)
        else:
            self._firing.discard(metric)

    def all_thresholds(self) -> dict[str, float | None]:
        return dict(self._thresholds)
