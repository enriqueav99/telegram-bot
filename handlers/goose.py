from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from handlers.auth import require_auth, require_module
from modules import goose_client

log = logging.getLogger(__name__)


@require_auth
@require_module("goose")
async def goose_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    prompt = " ".join(context.args) if context.args else ""
    if not prompt:
        await update.message.reply_text(
            "Uso: /goose <pregunta>\n\nEjemplo: /goose explícame qué hace el archivo bot.py"
        )
        return

    thinking = await update.message.reply_text("🤔 Goose está pensando…")

    result = await goose_client.run(prompt)

    chunks = goose_client._split(result)
    await thinking.edit_text(chunks[0])
    for chunk in chunks[1:]:
        await update.message.reply_text(chunk)
