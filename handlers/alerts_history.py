from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from handlers.auth import require_auth
from modules import alert_history

log = logging.getLogger(__name__)

STATUS_ICON = {"firing": "🔴", "resolved": "🟢"}


@require_auth
async def alerts_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    alerts = alert_history.recent(15)

    if not alerts:
        await update.message.reply_text("No hay alertas recientes registradas.")
        return

    lines = ["🔔 *Alertas recientes*\n"]
    for a in reversed(alerts):
        ts = a["ts"][:16].replace("T", " ")
        icon = STATUS_ICON.get(a["status"], "❓")
        source = a.get("source", "")
        name = a["name"]
        summary = a.get("summary", "")
        line = f"{icon} `{ts}` *{name}*"
        if source:
            line += f" [{source}]"
        if summary:
            line += f"\n   _{summary}_"
        lines.append(line)

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@require_auth
async def alerts_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    alert_history.clear()
    await update.message.reply_text("🗑 Historial de alertas borrado.")
