from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from handlers.auth import require_auth, require_module

log = logging.getLogger(__name__)


@require_auth
@require_module("ask")
async def ask_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from modules.claude_client import ClaudeClient
    client: ClaudeClient = context.bot_data["claude"]

    if not client.available:
        await update.message.reply_text("❌ ANTHROPIC_API_KEY no configurada.")
        return

    question = " ".join(context.args).strip() if context.args else ""
    if not question:
        await update.message.reply_text(
            "Uso: `/ask <pregunta>`\n\nEjemplos:\n"
            "• `/ask cuánta RAM libre hay?`\n"
            "• `/ask qué proceso consume más CPU?`\n"
            "• `/ask muéstrame los logs de nginx`",
            parse_mode="Markdown",
        )
        return

    chat_id = str(update.effective_chat.id)
    await update.effective_chat.send_action("typing")
    msg = await update.message.reply_text("⏳ Consultando a Claude...")

    response = await client.chat(chat_id, question)
    try:
        await msg.edit_text(response)
    except Exception:
        await update.message.reply_text(response)


@require_auth
@require_module("ask")
async def ask_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from modules.claude_client import ClaudeClient
    client: ClaudeClient = context.bot_data["claude"]
    chat_id = str(update.effective_chat.id)
    client.reset(chat_id)
    await update.message.reply_text("🗑 Historial de conversación con Claude borrado.")
