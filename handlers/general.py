from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from handlers.auth import require_auth
from modules import docker_client, system_client

CLAUDE_BOT_STATUS_FILE = Path("/app/data/claude-bot-status.json")


def _claude_bot_status() -> str:
    try:
        data = json.loads(CLAUDE_BOT_STATUS_FILE.read_text())
        updated = datetime.fromisoformat(data["updated_at"])
        age_s = int((datetime.now(UTC) - updated).total_seconds())
        if age_s > 120:
            return f"🤖 Claude Bot: ⚠️ sin actividad hace {age_s}s"
        sessions = data.get("session_count", 0)
        return f"🤖 Claude Bot: ✅ activo  ({sessions} sesiones)"
    except FileNotFoundError:
        return "🤖 Claude Bot: ❓ sin datos"
    except Exception:
        return "🤖 Claude Bot: ❌ error leyendo estado"


log = logging.getLogger(__name__)

HELP_TEXT = """
🤖 *Bot de Homelab*

*Servidor:*
/status — Resumen rápido del servidor
/metrics — Métricas detalladas del sistema
/docker — Panel de contenedores Docker

*Utilidades:*
/speedtest — Test de velocidad de internet
/note \\<texto\\> — Guardar una nota
/note del \\<id\\> — Eliminar una nota
/notes — Ver todas las notas
/digest — Ver/cambiar hora del resumen diario
/torrents — Lista de torrents activos
/torrent \\<magnet\\> — Añadir torrent
/ssh — Ejecutar comandos en el servidor
/sshadd \\<alias\\> \\<cmd\\> — Registrar comando SSH
/sshdel \\<alias\\> — Eliminar comando SSH

*General:*
/panel — Panel de control \\(activar/desactivar módulos\\)
/help — Esta ayuda

_Los módulos desactivados no responden sus comandos\\. Actívalos desde /panel\\._
"""


@require_auth
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Hola {user.first_name}\\! Soy el bot de tu homelab\\.\n\n"
        "Usa /help para ver los comandos disponibles\\.\n"
        "Usa /panel para activar o desactivar módulos\\.",
        parse_mode="MarkdownV2",
    )


@require_auth
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode="MarkdownV2")


@require_auth
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    features = context.bot_data["features"]
    docker: docker_client.DockerClient = context.bot_data["docker"]
    lines: list[str] = ["📡 *Estado del homelab*\n"]

    if features.is_enabled("system"):
        snap = system_client.snapshot()
        lines.append(
            f"🖥️ CPU: {snap.cpu_percent:.1f}%  |  "
            f"RAM: {snap.ram_used_gb:.1f}/{snap.ram_total_gb:.1f} GB  |  "
            f"Uptime: {snap.uptime_str()}"
        )
        lines.append(
            f"💿 Disco: {snap.disk_used_gb:.1f}/{snap.disk_total_gb:.1f} GB "
            f"({snap.disk_percent:.0f}%)"
        )
        lines.append(f"🌐 Red: ↑ {snap.net_sent_mb:.0f} MB  ↓ {snap.net_recv_mb:.0f} MB")
    else:
        lines.append("📊 Métricas: _módulo desactivado_")

    lines.append("")

    if features.is_enabled("docker"):
        if docker.available:
            running, total = docker.running_count()
            lines.append(f"🐳 Contenedores: {running} activos / {total} total")
        else:
            lines.append("🐳 Docker: _socket no disponible_")
    else:
        lines.append("🐳 Docker: _módulo desactivado_")

    lines.append("")
    lines.append(_claude_bot_status())

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
