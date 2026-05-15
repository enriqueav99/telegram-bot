from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

FEATURES_FILE = Path("data/features.json")

DEFAULT_FEATURES: dict[str, bool] = {
    "docker": True,
    "system": True,
    "alerts": False,
    "grafana": False,
    "radarr": False,
    "sonarr": False,
    "crowdsec": False,
    "speedtest": True,
    "notes": True,
    "digest": False,
    "qbittorrent": False,
    "shell": False,
    "ask": False,
    "wireguard": False,
    "github_actions": False,
    "reminders": True,
    "todo": True,
    "snippets": True,
    "cron": False,
    "weather": True,
    "sysalerts": False,
}

FEATURE_LABELS: dict[str, str] = {
    "docker": "🐳 Docker Monitor",
    "system": "📊 Métricas del sistema",
    "alerts": "🔔 Alertmanager",
    "grafana": "📈 Grafana Alerts",
    "radarr": "🎬 Radarr",
    "sonarr": "📺 Sonarr",
    "crowdsec": "🛡️ CrowdSec",
    "speedtest": "🌐 Speedtest",
    "notes": "📝 Notas",
    "digest": "🌅 Resumen diario",
    "qbittorrent": "🧲 qBittorrent",
    "shell": "🖥️ Comandos del servidor",
    "ask": "🤖 Claude (API)",
    "wireguard": "🔒 WireGuard VPN",
    "github_actions": "🔧 GitHub Actions",
    "reminders": "⏰ Recordatorios",
    "todo": "📋 Lista de tareas",
    "snippets": "💾 Snippets",
    "cron": "⏱️ Cron (programador)",
    "weather": "🌤️ Tiempo",
    "sysalerts": "🔔 Alertas de sistema",
}


@dataclass(frozen=True)
class BotConfig:
    token: str
    allowed_users: frozenset[int]
    alerts_port: int
    alerts_chat_id: int | None
    log_level: str
    github_token: str
    github_repo: str
    prometheus_url: str

    @classmethod
    def load(cls) -> BotConfig:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN no está definido")

        raw_users = os.getenv("ALLOWED_USERS", "")
        allowed = frozenset(int(u.strip()) for u in raw_users.split(",") if u.strip())

        raw_chat = os.getenv("ALERTS_CHAT_ID")

        return cls(
            token=token,
            allowed_users=allowed,
            alerts_port=int(os.getenv("ALERTS_PORT", "9091")),
            alerts_chat_id=int(raw_chat) if raw_chat else None,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            github_token=os.getenv("GITHUB_TOKEN", ""),
            github_repo=os.getenv("GITHUB_REPO", ""),
            prometheus_url=os.getenv("PROMETHEUS_URL", ""),
        )


class FeatureFlags:
    def __init__(self) -> None:
        FEATURES_FILE.parent.mkdir(parents=True, exist_ok=True)
        if FEATURES_FILE.exists():
            saved: dict[str, bool] = json.loads(FEATURES_FILE.read_text())
            self._flags = {**DEFAULT_FEATURES, **saved}
        else:
            self._flags = dict(DEFAULT_FEATURES)
        self._save()

    def is_enabled(self, feature: str) -> bool:
        return self._flags.get(feature, False)

    def toggle(self, feature: str) -> bool:
        if feature not in DEFAULT_FEATURES:
            raise ValueError(f"Feature desconocida: {feature}")
        self._flags[feature] = not self._flags[feature]
        self._save()
        return self._flags[feature]

    def all(self) -> dict[str, bool]:
        return dict(self._flags)

    def _save(self) -> None:
        FEATURES_FILE.write_text(json.dumps(self._flags, indent=2))
