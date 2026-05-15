"""Gestión de snippets de texto y código."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from handlers.auth import require_auth, require_module
from modules import snippets_client

log = logging.getLogger(__name__)

MAX_PREVIEW = 60
MAX_OUTPUT = 3800


@require_auth
@require_module("snippets")
async def snip_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []

    if not args:
        await _list_snips(update)
        return

    name = args[0].lower()

    if len(args) == 1:
        content = snippets_client.get(name)
        if content is None:
            await update.message.reply_text(
                f"❌ No existe el snippet `{name}`.\n\nUsa `/snips` para ver los disponibles.",
                parse_mode="Markdown",
            )
            return
        if len(content) > MAX_OUTPUT:
            content = content[:MAX_OUTPUT] + "\n…"
        await update.message.reply_text(f"`{name}`:\n```\n{content}\n```", parse_mode="Markdown")
    else:
        content = " ".join(args[1:])
        snippets_client.add(name, content)
        await update.message.reply_text(f"💾 Snippet `{name}` guardado.", parse_mode="Markdown")


@require_auth
@require_module("snippets")
async def snipdel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if not args:
        await update.message.reply_text("Uso: `/snipdel <nombre>`", parse_mode="Markdown")
        return
    name = args[0].lower()
    if snippets_client.delete(name):
        await update.message.reply_text(f"🗑️ Snippet `{name}` eliminado.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ No existe el snippet `{name}`.", parse_mode="Markdown")


@require_auth
@require_module("snippets")
async def snips_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _list_snips(update)


async def _list_snips(update: Update) -> None:
    snips = snippets_client.list_all()
    if not snips:
        await update.message.reply_text(
            "📭 No hay snippets guardados.\n\nAñade uno con:\n`/snip <nombre> <contenido>`",
            parse_mode="Markdown",
        )
        return
    lines = ["💾 *Snippets guardados:*\n"]
    for name in sorted(snips.keys()):
        preview = snips[name]["content"][:MAX_PREVIEW].replace("\n", "↵")
        suffix = "…" if len(snips[name]["content"]) > MAX_PREVIEW else ""
        lines.append(f"`{name}` — _{preview}{suffix}_")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
