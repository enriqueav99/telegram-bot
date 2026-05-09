from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from handlers.auth import require_auth, require_module
from modules import notes_client

log = logging.getLogger(__name__)


@require_auth
@require_module("notes")
async def note_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []

    if not args:
        await update.message.reply_text(
            "Uso:\n"
            "`/note <texto>` — añadir nota\n"
            "`/note del <id>` — eliminar nota\n"
            "`/notes` — ver todas",
            parse_mode="Markdown",
        )
        return

    if args[0] == "del":
        if len(args) < 2 or not args[1].isdigit():
            await update.message.reply_text("Uso: `/note del <id>`", parse_mode="Markdown")
            return
        note_id = int(args[1])
        if notes_client.delete(note_id):
            await update.message.reply_text(f"🗑️ Nota #{note_id} eliminada")
        else:
            await update.message.reply_text(f"❌ No existe la nota #{note_id}")
        return

    text = " ".join(args)
    note_id = notes_client.add(text)
    await update.message.reply_text(f"📝 Nota #{note_id} guardada")


@require_auth
@require_module("notes")
async def notes_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    all_notes = notes_client.list_all()
    if not all_notes:
        await update.message.reply_text("📭 No hay notas guardadas")
        return
    lines = ["📝 *Notas guardadas:*\n"]
    for n in all_notes:
        lines.append(f"`#{n['id']}` {n['text']}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
