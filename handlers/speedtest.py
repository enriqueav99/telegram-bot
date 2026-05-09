from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes

from handlers.auth import require_auth, require_module
from modules import speedtest_client

log = logging.getLogger(__name__)


@require_auth
@require_module("speedtest")
async def speedtest_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.message.reply_text("⏳ Ejecutando speedtest, espera ~30s…")
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, speedtest_client.run)
        await msg.edit_text(result.format(), parse_mode="Markdown")
    except Exception as exc:
        log.exception("Speedtest failed")
        await msg.edit_text(f"❌ Error al ejecutar speedtest: {exc}")
