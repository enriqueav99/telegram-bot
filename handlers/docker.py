from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from handlers.auth import require_auth, require_module
from modules.docker_client import DockerClient

log = logging.getLogger(__name__)

PAGE_SIZE = 10


def _container_list_keyboard(containers, page: int = 0) -> InlineKeyboardMarkup:
    start = page * PAGE_SIZE
    page_items = containers[start : start + PAGE_SIZE]
    buttons = []
    for c in page_items:
        buttons.append(
            [
                InlineKeyboardButton(
                    f"{c.emoji} {c.name}", callback_data=f"docker:detail:{c.short_id}"
                )
            ]
        )
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"docker:list:{page - 1}"))
    if start + PAGE_SIZE < len(containers):
        nav.append(InlineKeyboardButton("Siguiente ➡️", callback_data=f"docker:list:{page + 1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("🔄 Actualizar", callback_data="docker:list:0")])
    return InlineKeyboardMarkup(buttons)


def _detail_keyboard(short_id: str, status: str) -> InlineKeyboardMarkup:
    buttons = []
    if status != "running":
        buttons.append(InlineKeyboardButton("▶️ Iniciar", callback_data=f"docker:start:{short_id}"))
    if status == "running":
        buttons.append(InlineKeyboardButton("⏹️ Detener", callback_data=f"docker:stop:{short_id}"))
    buttons2 = [InlineKeyboardButton("🔄 Reiniciar", callback_data=f"docker:restart:{short_id}")]
    buttons3 = [InlineKeyboardButton("📋 Logs", callback_data=f"docker:logs:{short_id}")]
    buttons4 = [InlineKeyboardButton("⬅️ Lista", callback_data="docker:list:0")]
    rows = []
    if buttons:
        rows.append(buttons)
    rows.append(buttons2)
    rows.append(buttons3)
    rows.append(buttons4)
    return InlineKeyboardMarkup(rows)


@require_auth
@require_module("docker")
async def docker_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    docker: DockerClient = context.bot_data["docker"]
    if not docker.available:
        await update.message.reply_text("❌ Docker socket no disponible.")
        return
    containers = docker.list_containers()
    running = sum(1 for c in containers if c.status == "running")
    text = f"🐳 *Contenedores Docker* — {running} activos / {len(containers)} total"
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=_container_list_keyboard(containers, page=0),
    )


async def docker_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config = context.bot_data["config"]
    features = context.bot_data["features"]
    user = update.effective_user

    if config.allowed_users and user.id not in config.allowed_users:
        await query.answer("⛔ Sin permiso", show_alert=True)
        return

    if not features.is_enabled("docker"):
        await query.answer("Módulo Docker desactivado", show_alert=True)
        return

    docker: DockerClient = context.bot_data["docker"]
    if not docker.available:
        await query.answer("Docker socket no disponible", show_alert=True)
        return

    data: str = query.data
    parts = data.split(":", 2)
    action = parts[1]

    if action == "list":
        page = int(parts[2]) if len(parts) > 2 else 0
        containers = docker.list_containers()
        running = sum(1 for c in containers if c.status == "running")
        text = f"🐳 *Contenedores Docker* — {running} activos / {len(containers)} total"
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=_container_list_keyboard(containers, page),
        )

    elif action == "detail":
        short_id = parts[2]
        c = docker.get_container(short_id)
        if not c:
            await query.answer("Contenedor no encontrado", show_alert=True)
            return
        detail = docker.container_detail(short_id)
        lines = [
            f"🐳 *{c.name}*\n",
            f"Estado: {c.status}",
            f"Imagen: `{detail.get('image_tag', c.short_id)}`",
        ]
        if "uptime" in detail:
            lines.append(f"Uptime: {detail['uptime']}")
        if "mem_mb" in detail:
            lines.append(f"Memoria: {detail['mem_mb']:.0f} / {detail['mem_limit_mb']:.0f} MB")
        await query.edit_message_text(
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=_detail_keyboard(c.short_id, c.status),
        )

    elif action in ("start", "stop", "restart"):
        short_id = parts[2]
        if action == "start":
            result = docker.start(short_id)
        elif action == "stop":
            result = docker.stop(short_id)
        else:
            result = docker.restart(short_id)
        await query.answer(result)
        c = docker.get_container(short_id)
        if c:
            text = (
                f"🐳 *{c.name}*\n\n"
                f"Estado: {c.status}\n"
                f"Imagen: `{c.image.tags[0] if c.image.tags else c.image.short_id}`"
            )
            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=_detail_keyboard(c.short_id, c.status),
            )

    elif action == "logs":
        short_id = parts[2]
        logs = docker.logs(short_id, lines=30)
        MAX = 4000
        if len(logs) > MAX:
            logs = "...\n" + logs[-MAX:]
        c = docker.get_container(short_id)
        name = c.name if c else short_id
        await query.message.reply_text(f"📋 Logs de {name} (últimas 30 líneas):\n\n{logs}")
