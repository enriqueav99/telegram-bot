from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from handlers.auth import require_auth, require_module
from modules import system_client

log = logging.getLogger(__name__)


@require_auth
@require_module("system")
async def metrics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    snap = system_client.snapshot()
    await update.message.reply_text(snap.format(), parse_mode="Markdown")
