"""Logs de contenedores Docker."""

from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from handlers.auth import require_auth, require_module
from modules.docker_client import ContainerInfo, DockerClient

log = logging.getLogger(__name__)

MAX_OUTPUT = 3800
TAIL_LINES = 50


def _containers_keyboard(containers: list[ContainerInfo]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(f"{c.emoji} {c.name}", callback_data=f"logs:tail:{c.name}")]
        for c in containers
    ]
    return InlineKeyboardMarkup(buttons)


@require_auth
@require_module("logs")
async def logs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    docker: DockerClient = context.bot_data["docker"]
    if not docker.available:
        await update.message.reply_text("❌ Docker socket no disponible.")
        return
    containers = docker.list_containers(all=True)
    if not containers:
        await update.message.reply_text("📭 No hay contenedores.")
        return
    await update.message.reply_text(
        "📄 *Logs de contenedores* — selecciona uno:",
        parse_mode="Markdown",
        reply_markup=_containers_keyboard(containers),
    )


async def logs_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config_bot = context.bot_data["config"]
    features = context.bot_data["features"]
    user = update.effective_user

    if config_bot.allowed_users and user.id not in config_bot.allowed_users:
        return
    if not features.is_enabled("logs"):
        return

    docker: DockerClient = context.bot_data["docker"]
    parts = query.data.split(":", 2)
    if len(parts) < 3 or parts[1] != "tail":
        return

    name = parts[2]
    msg = await query.message.reply_text(f"⏳ Leyendo logs de `{name}`...", parse_mode="Markdown")
    output = docker.logs(name, lines=TAIL_LINES)
    if len(output) > MAX_OUTPUT:
        output = "…\n" + output[-MAX_OUTPUT:]
    await msg.edit_text(
        f"📄 *{name}* (últimas {TAIL_LINES} líneas):\n```\n{output}\n```",
        parse_mode="Markdown",
    )
