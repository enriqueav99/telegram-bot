from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from handlers.auth import require_auth, require_module
from modules import docker_client as docker_mod
from modules import system_client

log = logging.getLogger(__name__)

DIGEST_JOB_NAME = "daily_digest"
DIGEST_CONFIG_FILE = Path("data/digest.json")
DEFAULT_HOUR, DEFAULT_MINUTE = 8, 0


def load_config() -> tuple[int, int]:
    if DIGEST_CONFIG_FILE.exists():
        data = json.loads(DIGEST_CONFIG_FILE.read_text())
        return data.get("hour", DEFAULT_HOUR), data.get("minute", DEFAULT_MINUTE)
    return DEFAULT_HOUR, DEFAULT_MINUTE


def _save_config(hour: int, minute: int) -> None:
    DIGEST_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    DIGEST_CONFIG_FILE.write_text(json.dumps({"hour": hour, "minute": minute}))


def schedule(job_queue, hour: int, minute: int) -> None:
    for job in job_queue.get_jobs_by_name(DIGEST_JOB_NAME):
        job.schedule_removal()
    job_queue.run_daily(
        _digest_job,
        time=datetime.time(hour=hour, minute=minute, tzinfo=datetime.UTC),
        name=DIGEST_JOB_NAME,
    )


async def _digest_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    features = context.bot_data["features"]
    config = context.bot_data["config"]
    docker: docker_mod.DockerClient = context.bot_data["docker"]

    if not features.is_enabled("digest") or not config.alerts_chat_id:
        return

    lines = ["🌅 *Resumen diario del homelab*\n"]

    if features.is_enabled("system"):
        snap = system_client.snapshot()
        lines.append(
            f"🖥️ CPU: {snap.cpu_percent:.1f}%  |  "
            f"RAM: {snap.ram_used_gb:.1f}/{snap.ram_total_gb:.1f} GB  |  "
            f"Uptime: {snap.uptime_str()}"
        )
        lines.append(
            f"💿 Disco: {snap.disk_used_gb:.1f}/{snap.disk_total_gb:.1f} GB "
            f"({snap.disk_percent:.0f}%)"
        )
        lines.append(f"🌐 Red: ↑ {snap.net_sent_mb:.0f} MB  ↓ {snap.net_recv_mb:.0f} MB")
        lines.append("")

    if features.is_enabled("docker") and docker.available:
        running, total = docker.running_count()
        lines.append(f"🐳 Contenedores: {running} activos / {total} total")

    await context.bot.send_message(
        chat_id=config.alerts_chat_id,
        text="\n".join(lines),
        parse_mode="Markdown",
    )


@require_auth
@require_module("digest")
async def digest_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    hour, minute = load_config()

    if not context.args:
        await update.message.reply_text(
            f"🌅 *Resumen diario* activo\n"
            f"Hora configurada: *{hour:02d}:{minute:02d} UTC*\n\n"
            "Para cambiar la hora: `/digest HH:MM`",
            parse_mode="Markdown",
        )
        return

    raw = context.args[0]
    try:
        h_str, m_str = raw.split(":")
        h, m = int(h_str), int(m_str)
        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "Formato inválido. Usa: `/digest HH:MM`", parse_mode="Markdown"
        )
        return

    _save_config(h, m)
    schedule(context.application.job_queue, h, m)
    await update.message.reply_text(
        f"✅ Resumen diario configurado para las *{h:02d}:{m:02d} UTC*",
        parse_mode="Markdown",
    )
