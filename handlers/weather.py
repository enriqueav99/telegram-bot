"""Consulta del tiempo."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from handlers.auth import require_auth, require_module
from modules import weather_client

log = logging.getLogger(__name__)


@require_auth
@require_module("weather")
async def weather_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if not args:
        await update.message.reply_text(
            "Uso: `/weather <ciudad>`\n\n*Ejemplos:*\n`/weather Madrid`\n`/weather New York`",
            parse_mode="Markdown",
        )
        return

    city = " ".join(args)
    msg = await update.message.reply_text(
        f"⏳ Consultando el tiempo en *{city}*…", parse_mode="Markdown"
    )
    try:
        result = await weather_client.get_weather(city)
        await msg.edit_text(result, parse_mode="Markdown")
    except Exception as exc:
        log.exception("Weather lookup failed for city=%s", city)
        await msg.edit_text(f"❌ Error consultando el tiempo: {exc}")
