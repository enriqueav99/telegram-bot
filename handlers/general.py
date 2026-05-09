from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from handlers.auth import require_auth
from modules import docker_client, system_client

log = logging.getLogger(__name__)

HELP_TEXT = """
🤖 *Bot de Homelab*

*Comandos disponibles:*

/status — Resumen rápido del servidor
/metrics — Métricas detalladas del sistema
/docker — Panel de contenedores Docker
/panel — Panel de control \\(activar/desactivar módulos\\)
/help — Esta ayuda

_Los módulos desactivados no responden sus comandos\\. Actívalos desde /panel\\._

*Webhooks \\(puerto 9091\\):*

`POST /alerts` — Alertmanager
`POST /grafana` — Grafana Unified Alerting
`POST /radarr` — Radarr \\(películas\\)
`POST /sonarr` — Sonarr \\(series\\)
`POST /crowdsec` — CrowdSec
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

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
