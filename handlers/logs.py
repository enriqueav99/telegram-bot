from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from handlers.auth import require_auth, require_module
from modules import ssh_client
from modules.ssh_client import SSHConfig

log = logging.getLogger(__name__)

LOG_FILES: list[tuple[str, str]] = [
    ("nginx access", "/var/log/nginx/access.log"),
    ("nginx error", "/var/log/nginx/error.log"),
    ("syslog", "/var/log/syslog"),
    ("auth", "/var/log/auth.log"),
    ("docker", "/var/log/docker.log"),
    ("kernel", "/var/log/kern.log"),
]

MAX_OUTPUT = 3800


def _logs_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(label, callback_data=f"logs:tail:{i}")]
        for i, (label, _) in enumerate(LOG_FILES)
    ]
    return InlineKeyboardMarkup(buttons)


@require_auth
@require_module("ssh")
async def logs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: SSHConfig = context.bot_data["ssh_config"]
    if not config.available:
        await update.message.reply_text("❌ SSH_HOST no configurado.")
        return
    await update.message.reply_text(
        "📄 *Logs del servidor* — selecciona un fichero:",
        parse_mode="Markdown",
        reply_markup=_logs_keyboard(),
    )


async def logs_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    config_bot = context.bot_data["config"]
    features = context.bot_data["features"]
    user = update.effective_user

    if config_bot.allowed_users and user.id not in config_bot.allowed_users:
        await query.answer("⛔ Sin permiso", show_alert=True)
        return
    if not features.is_enabled("ssh"):
        await query.answer("Módulo SSH desactivado", show_alert=True)
        return

    ssh_config: SSHConfig = context.bot_data["ssh_config"]
    parts = query.data.split(":", 2)
    action = parts[1]

    if action == "tail":
        idx = int(parts[2])
        label, path = LOG_FILES[idx]
        msg = await query.message.reply_text(f"⏳ Leyendo `{label}`...", parse_mode="Markdown")
        try:
            stdout, stderr, _ = await ssh_client.run(ssh_config, f"tail -50 {path} 2>/dev/null || echo '(fichero no encontrado)'")
            output = stdout or stderr or "(sin salida)"
            if len(output) > MAX_OUTPUT:
                output = "…\n" + output[-MAX_OUTPUT:]
            await msg.edit_text(
                f"📄 *{label}* (últimas 50 líneas):\n```\n{output}\n```",
                parse_mode="Markdown",
            )
        except Exception as exc:
            await msg.edit_text(f"❌ Error SSH: {exc}")
