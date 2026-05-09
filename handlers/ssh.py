from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from handlers.auth import require_auth, require_module
from modules import ssh_client
from modules.ssh_client import SSHConfig

log = logging.getLogger(__name__)

MAX_OUTPUT = 3800


def _commands_keyboard(commands: dict[str, str]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(f"▶️ {alias}", callback_data=f"ssh:run:{alias}")]
        for alias in sorted(commands)
    ]
    buttons.append([InlineKeyboardButton("🔄 Actualizar", callback_data="ssh:list")])
    return InlineKeyboardMarkup(buttons)


@require_auth
@require_module("ssh")
async def ssh_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: SSHConfig = context.bot_data["ssh_config"]
    if not config.available:
        await update.message.reply_text("❌ SSH_HOST no configurado.")
        return
    commands = ssh_client.load_commands()
    if not commands:
        await update.message.reply_text(
            "📭 No hay comandos configurados.\n\n"
            "Añade uno con:\n`/sshadd <alias> <comando>`",
            parse_mode="Markdown",
        )
        return
    await update.message.reply_text(
        f"🖥️ *SSH — {config.host}*\nSelecciona un comando:",
        parse_mode="Markdown",
        reply_markup=_commands_keyboard(commands),
    )


@require_auth
@require_module("ssh")
async def sshadd_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text(
            "Uso: `/sshadd <alias> <comando>`\n\nEjemplo:\n`/sshadd logs-nginx tail -n 50 /var/log/nginx/error.log`",
            parse_mode="Markdown",
        )
        return
    alias = args[0]
    if len(alias) > 30:
        await update.message.reply_text("❌ El alias no puede tener más de 30 caracteres.")
        return
    command = " ".join(args[1:])
    ssh_client.add_command(alias, command)
    await update.message.reply_text(f"✅ Comando `{alias}` guardado:\n`{command}`", parse_mode="Markdown")


@require_auth
@require_module("ssh")
async def sshdel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if not args:
        await update.message.reply_text("Uso: `/sshdel <alias>`", parse_mode="Markdown")
        return
    alias = args[0]
    if ssh_client.remove_command(alias):
        await update.message.reply_text(f"🗑️ Comando `{alias}` eliminado.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ No existe el comando `{alias}`.", parse_mode="Markdown")


async def ssh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

    if action == "list":
        commands = ssh_client.load_commands()
        if not commands:
            await query.edit_message_text("📭 No hay comandos configurados.")
            return
        await query.edit_message_text(
            f"🖥️ *SSH — {ssh_config.host}*\nSelecciona un comando:",
            parse_mode="Markdown",
            reply_markup=_commands_keyboard(commands),
        )

    elif action == "run":
        alias = parts[2]
        commands = ssh_client.load_commands()
        command = commands.get(alias)
        if not command:
            await query.answer("Comando no encontrado", show_alert=True)
            return

        await query.answer(f"Ejecutando: {alias}…")
        msg = await query.message.reply_text(f"⏳ Ejecutando `{alias}`…", parse_mode="Markdown")

        try:
            stdout, stderr, exit_code = await ssh_client.run(ssh_config, command)
            output = stdout or stderr or "(sin salida)"
            if len(output) > MAX_OUTPUT:
                output = "…\n" + output[-MAX_OUTPUT:]
            icon = "✅" if exit_code == 0 else "⚠️"
            await msg.edit_text(
                f"{icon} `{alias}` (exit {exit_code}):\n\n```\n{output}\n```",
                parse_mode="Markdown",
            )
        except Exception as exc:
            log.exception("SSH run failed for alias=%s", alias)
            await msg.edit_text(f"❌ Error SSH: {exc}")
