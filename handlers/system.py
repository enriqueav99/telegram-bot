from __future__ import annotations

import asyncio
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


@require_auth
@require_module("system")
async def procs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⏳ Midiendo CPU...")
    system_client.top_processes()  # warm up cpu_percent counters
    await asyncio.sleep(1)
    processes = system_client.top_processes()

    if not processes:
        await update.message.reply_text("No se pudieron obtener los procesos.")
        return

    lines = ["📋 *Top procesos por CPU*\n"]
    for p in processes[:10]:
        lines.append(
            f"`{p.name[:18]:<18}` {p.cpu_percent:5.1f}% CPU  {p.mem_mb:6.0f} MB  (PID {p.pid})"
        )

    by_mem = sorted(processes, key=lambda x: x.mem_mb, reverse=True)
    lines.append("\n💾 *Top por memoria*\n")
    for p in by_mem[:5]:
        lines.append(f"`{p.name[:18]:<18}` {p.mem_mb:6.0f} MB  {p.cpu_percent:5.1f}% CPU")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
