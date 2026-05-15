from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
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

_HELP_CATEGORIES: dict[str, dict] = {
    "server": {
        "label": "🖥️ Servidor",
        "commands": [
            ("/status", "Resumen rápido del servidor"),
            ("/metrics", "Métricas detalladas del sistema"),
            ("/procs", "Top procesos por CPU y memoria"),
            ("/docker", "Panel de contenedores Docker"),
            ("/logs", "Navegar logs del servidor"),
            ("/alerts", "Historial de alertas recibidas"),
            ("/alertsclear", "Limpiar historial de alertas"),
            ("/wg", "Estado de peers WireGuard VPN"),
            ("/ci", "Últimas ejecuciones de GitHub Actions"),
        ],
    },
    "organizar": {
        "label": "🗂️ Organización",
        "commands": [
            ("/todo", "Lista de tareas (add · done · del)"),
            ("/note <texto>", "Guardar nota rápida"),
            ("/notes", "Ver todas las notas"),
            ("/snip <nombre> <contenido>", "Guardar snippet"),
            ("/snip <nombre>", "Recuperar snippet"),
            ("/snips", "Ver todos los snippets"),
            ("/snipdel <nombre>", "Eliminar snippet"),
            ("/remind <cuándo> <texto>", "Programar recordatorio"),
            ("/reminders", "Ver recordatorios pendientes"),
            ("/reminddel <id>", "Cancelar recordatorio"),
        ],
        "footer": "_Formatos de tiempo para /remind:_ `30m` · `2h` · `1d` · `14:30` · `2026-06-01 10:00`",
    },
    "auto": {
        "label": "⚙️ Automatización",
        "commands": [
            ("/cmd", "Menú de comandos registrados"),
            ("/cmdadd <alias> <cmd>", "Registrar nuevo comando"),
            ("/cmddel <alias>", "Eliminar comando"),
            ("/restartai", "Ejecutar alias 'ai-bot'"),
            ("/cron add <horario> <alias>", "Programar comando recurrente"),
            ("/cron list", "Ver trabajos cron activos"),
            ("/cron del <id>", "Eliminar trabajo cron"),
            ("/digest", "Ver/cambiar hora del resumen diario"),
        ],
        "footer": "_Formatos de horario para /cron:_ `HH:MM` · `30m` · `6h`",
    },
    "utils": {
        "label": "🌐 Utilidades",
        "commands": [
            ("/calc <expresión>", "Calculadora (sqrt, sin, log…)"),
            ("/weather <ciudad>", "Tiempo actual + previsión 3 días"),
            ("/speedtest", "Test de velocidad de internet"),
            ("/torrents", "Lista de torrents activos"),
            ("/torrent <magnet>", "Añadir torrent por magnet/URL"),
        ],
    },
    "ask": {
        "label": "🤖 Asistente",
        "commands": [
            ("/ask <pregunta>", "Preguntar a Claude (mantiene historial)"),
            ("/askreset", "Reiniciar conversación con Claude"),
        ],
    },
    "alertas": {
        "label": "🔔 Alertas",
        "commands": [
            ("/sysalert", "Ver umbrales de alerta del sistema"),
            ("/sysalert cpu 85", "Alertar si CPU ≥ 85%"),
            ("/sysalert ram 90", "Alertar si RAM ≥ 90%"),
            ("/sysalert disk 85", "Alertar si disco ≥ 85%"),
            ("/sysalert cpu off", "Desactivar alerta de CPU"),
        ],
    },
}

_HELP_INTRO = (
    "🤖 *Bot de Homelab*\n\n"
    "Elige una categoría para ver sus comandos:\n\n"
    "_Activa o desactiva módulos desde /panel_"
)


def _main_keyboard() -> InlineKeyboardMarkup:
    cats = list(_HELP_CATEGORIES.items())
    rows = [[InlineKeyboardButton(v["label"], callback_data=f"help:cat:{k}")] for k, v in cats]
    return InlineKeyboardMarkup(rows)


def _category_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("← Volver", callback_data="help:back")]])


def _category_text(key: str) -> str:
    cat = _HELP_CATEGORIES[key]
    lines = [f"{cat['label']}\n"]
    for cmd, desc in cat["commands"]:
        lines.append(f"`{cmd}` — {desc}")
    if "footer" in cat:
        lines.append(f"\n{cat['footer']}")
    return "\n".join(lines)


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
    await update.message.reply_text(
        _HELP_INTRO, parse_mode="Markdown", reply_markup=_main_keyboard()
    )


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config_bot = context.bot_data["config"]
    if config_bot.allowed_users and update.effective_user.id not in config_bot.allowed_users:
        await query.answer("⛔ Sin permiso", show_alert=True)
        return

    parts = query.data.split(":", 2)
    action = parts[1]

    if action == "back":
        await query.edit_message_text(
            _HELP_INTRO, parse_mode="Markdown", reply_markup=_main_keyboard()
        )
    elif action == "cat" and len(parts) == 3 and parts[2] in _HELP_CATEGORIES:
        await query.edit_message_text(
            _category_text(parts[2]),
            parse_mode="Markdown",
            reply_markup=_category_keyboard(),
        )


@require_auth
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    features = context.bot_data["features"]
    docker: docker_client.DockerClient = context.bot_data["docker"]
    lines: list[str] = ["📡 *Estado del homelab*\n"]

    if features.is_enabled("system"):
        snap = await system_client.snapshot(context.bot_data.get("prometheus"))
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
