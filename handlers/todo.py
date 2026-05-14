"""Lista de tareas con estado pendiente/hecha."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from handlers.auth import require_auth, require_module
from modules import todo_client

log = logging.getLogger(__name__)

_HELP = (
    "Uso:\n"
    "`/todo add <texto>` — añadir tarea\n"
    "`/todo done <id>` — marcar como hecha\n"
    "`/todo del <id>` — eliminar\n"
    "`/todo` — ver lista"
)


@require_auth
@require_module("todo")
async def todo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []

    if not args:
        await _show_list(update)
        return

    action = args[0].lower()

    if action == "add":
        if len(args) < 2:
            await update.message.reply_text("Uso: `/todo add <texto>`", parse_mode="Markdown")
            return
        text = " ".join(args[1:])
        todo_id = todo_client.add(text)
        await update.message.reply_text(
            f"✅ Tarea #{todo_id} añadida: _{text}_", parse_mode="Markdown"
        )

    elif action == "done":
        if len(args) < 2 or not args[1].isdigit():
            await update.message.reply_text("Uso: `/todo done <id>`", parse_mode="Markdown")
            return
        todo_id = int(args[1])
        if todo_client.mark_done(todo_id):
            await update.message.reply_text(f"☑️ Tarea #{todo_id} completada")
        else:
            await update.message.reply_text(f"❌ No existe la tarea #{todo_id}")

    elif action == "del":
        if len(args) < 2 or not args[1].isdigit():
            await update.message.reply_text("Uso: `/todo del <id>`", parse_mode="Markdown")
            return
        todo_id = int(args[1])
        if todo_client.delete(todo_id):
            await update.message.reply_text(f"🗑️ Tarea #{todo_id} eliminada")
        else:
            await update.message.reply_text(f"❌ No existe la tarea #{todo_id}")

    else:
        await update.message.reply_text(_HELP, parse_mode="Markdown")


async def _show_list(update: Update) -> None:
    todos = todo_client.list_all()
    if not todos:
        await update.message.reply_text(
            "📭 No hay tareas. Añade una con `/todo add <texto>`", parse_mode="Markdown"
        )
        return

    pending = [t for t in todos if not t["done"]]
    done = [t for t in todos if t["done"]]

    lines = ["📋 *Lista de tareas*\n"]
    for t in pending:
        lines.append(f"⬜ `#{t['id']}` {t['text']}")
    if done:
        lines.append("")
        for t in done[-5:]:
            lines.append(f"✅ `#{t['id']}` {t['text']}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
