"""Recordatorios programados."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes

from handlers.auth import require_auth, require_module
from modules import reminder_client

log = logging.getLogger(__name__)

_DURATION_RE = re.compile(r"^(\d+)([mhd])$")
_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")
_DATETIME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{1,2}:\d{2})$")

_HELP = (
    "Uso: `/remind <cuándo> <texto>`\n\n"
    "*Ejemplos:*\n"
    "`/remind 30m revisar logs`\n"
    "`/remind 2h comprobar backup`\n"
    "`/remind 1d actualizar certificado`\n"
    "`/remind 14:30 reunión`\n"
    "`/remind 2026-06-01 10:00 llamada`"
)


def _parse_when(args: list[str]) -> tuple[datetime | None, list[str]]:
    """Returns (fire_at UTC, remaining args) or (None, args) if no valid time spec."""
    if not args:
        return None, args

    now = datetime.now(UTC)

    m = _DURATION_RE.match(args[0])
    if m:
        value, unit = int(m.group(1)), m.group(2)
        delta = {
            "m": timedelta(minutes=value),
            "h": timedelta(hours=value),
            "d": timedelta(days=value),
        }[unit]
        return now + delta, args[1:]

    m = _TIME_RE.match(args[0])
    if m:
        h, minute = int(m.group(1)), int(m.group(2))
        candidate = now.replace(hour=h, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate, args[1:]

    if len(args) >= 2:
        combined = f"{args[0]} {args[1]}"
        if _DATETIME_RE.match(combined):
            try:
                fire_at = datetime.fromisoformat(combined).replace(tzinfo=UTC)
                return fire_at, args[2:]
            except ValueError:
                pass

    return None, args


@require_auth
@require_module("reminders")
async def remind_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    fire_at, text_args = _parse_when(args)

    if fire_at is None or not text_args:
        await update.message.reply_text(_HELP, parse_mode="Markdown")
        return

    text = " ".join(text_args)
    chat_id = update.effective_chat.id
    reminder_id = reminder_client.add(chat_id, text, fire_at)

    delay = max((fire_at - datetime.now(UTC)).total_seconds(), 1)
    context.job_queue.run_once(
        _fire_reminder,
        when=delay,
        name=f"reminder_{reminder_id}",
        data={"id": reminder_id, "chat_id": chat_id, "text": text},
        chat_id=chat_id,
    )

    when_str = fire_at.strftime("%d/%m/%Y %H:%M UTC")
    await update.message.reply_text(
        f"⏰ Recordatorio #{reminder_id} para *{when_str}*:\n_{text}_",
        parse_mode="Markdown",
    )


@require_auth
@require_module("reminders")
async def reminders_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pending = reminder_client.list_pending(update.effective_chat.id)
    if not pending:
        await update.message.reply_text("📭 No hay recordatorios pendientes")
        return
    lines = ["⏰ *Recordatorios pendientes:*\n"]
    for r in pending:
        fire_at = datetime.fromisoformat(r["fire_at"])
        lines.append(f"`#{r['id']}` {fire_at.strftime('%d/%m %H:%M')} UTC — {r['text']}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@require_auth
@require_module("reminders")
async def reminddel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if not args or not args[0].isdigit():
        await update.message.reply_text("Uso: `/reminddel <id>`", parse_mode="Markdown")
        return

    reminder_id = int(args[0])
    if reminder_client.delete(reminder_id, update.effective_chat.id):
        for job in context.job_queue.get_jobs_by_name(f"reminder_{reminder_id}"):
            job.schedule_removal()
        await update.message.reply_text(f"🗑️ Recordatorio #{reminder_id} eliminado")
    else:
        await update.message.reply_text(f"❌ No existe el recordatorio #{reminder_id}")


async def _fire_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    data = context.job.data
    reminder_client.mark_done(data["id"])
    await context.bot.send_message(
        chat_id=data["chat_id"],
        text=f"⏰ *Recordatorio:*\n{data['text']}",
        parse_mode="Markdown",
    )


def schedule_pending(job_queue) -> None:
    """Re-schedule all pending reminders after a bot restart."""
    now = datetime.now(UTC)
    for r in reminder_client.list_all_pending():
        fire_at = datetime.fromisoformat(r["fire_at"])
        if fire_at.tzinfo is None:
            fire_at = fire_at.replace(tzinfo=UTC)
        delay = max((fire_at - now).total_seconds(), 5)
        job_queue.run_once(
            _fire_reminder,
            when=delay,
            name=f"reminder_{r['id']}",
            data={"id": r["id"], "chat_id": r["chat_id"], "text": r["text"]},
            chat_id=r["chat_id"],
        )
