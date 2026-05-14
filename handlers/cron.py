"""Comandos de shell programados con horario recurrente."""

from __future__ import annotations

import datetime
import logging

from telegram import Update
from telegram.ext import ContextTypes

from handlers.auth import require_auth, require_module
from modules import cron_client, shell_client

log = logging.getLogger(__name__)

_JOB_PREFIX = "cron_"

_HELP = (
    "Uso:\n"
    "`/cron add <horario> <alias>` — programar comando\n"
    "`/cron del <id>` — eliminar\n"
    "`/cron list` — ver programados\n\n"
    "*Formatos de horario:*\n"
    "`HH:MM` — todos los días a esa hora (UTC)\n"
    "`30m` — cada 30 minutos (mínimo 5m)\n"
    "`6h` — cada 6 horas"
)


@require_auth
@require_module("cron")
async def cron_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []

    if not args or args[0].lower() == "list":
        await _list_jobs(update)
        return

    action = args[0].lower()

    if action == "add":
        if len(args) < 3:
            await update.message.reply_text(_HELP, parse_mode="Markdown")
            return

        schedule_str, alias = args[1], args[2]
        schedule_data = cron_client.parse_schedule(schedule_str)
        if schedule_data is None:
            await update.message.reply_text(
                f"❌ Horario `{schedule_str}` no válido.\n\nUsa: `HH:MM`, `30m` o `6h`.",
                parse_mode="Markdown",
            )
            return

        commands = shell_client.load_commands()
        if alias not in commands:
            await update.message.reply_text(
                f"❌ El alias `{alias}` no existe.\n\nRegístralo con `/cmdadd {alias} <comando>`.",
                parse_mode="Markdown",
            )
            return

        chat_id = update.effective_chat.id
        job_id = cron_client.add(alias, schedule_str, chat_id)
        _schedule_job(context.job_queue, job_id, alias, schedule_data, chat_id)

        await update.message.reply_text(
            f"⏱️ Comando `{alias}` programado cada `{schedule_str}` (ID `{job_id}`).",
            parse_mode="Markdown",
        )

    elif action == "del":
        if len(args) < 2 or not args[1].isdigit():
            await update.message.reply_text("Uso: `/cron del <id>`", parse_mode="Markdown")
            return
        job_id = int(args[1])
        if cron_client.delete(job_id):
            for job in context.job_queue.get_jobs_by_name(f"{_JOB_PREFIX}{job_id}"):
                job.schedule_removal()
            await update.message.reply_text(f"🗑️ Cron #{job_id} eliminado.")
        else:
            await update.message.reply_text(f"❌ No existe el cron #{job_id}.")

    else:
        await update.message.reply_text(_HELP, parse_mode="Markdown")


async def _list_jobs(update: Update) -> None:
    jobs = cron_client.list_all()
    if not jobs:
        await update.message.reply_text(
            "📭 No hay comandos programados.\n\nAñade uno con:\n`/cron add <horario> <alias>`",
            parse_mode="Markdown",
        )
        return
    lines = ["⏱️ *Comandos programados:*\n"]
    for j in jobs:
        lines.append(f"`#{j['id']}` `{j['alias']}` — cada `{j['schedule']}`")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


def _schedule_job(job_queue, job_id: int, alias: str, schedule_data: dict, chat_id: int) -> None:
    name = f"{_JOB_PREFIX}{job_id}"
    data = {"job_id": job_id, "alias": alias, "chat_id": chat_id}
    if schedule_data["type"] == "daily":
        job_queue.run_daily(
            _run_cron_job,
            time=datetime.time(
                hour=schedule_data["hour"],
                minute=schedule_data["minute"],
                tzinfo=datetime.UTC,
            ),
            name=name,
            data=data,
            chat_id=chat_id,
        )
    else:
        job_queue.run_repeating(
            _run_cron_job,
            interval=schedule_data["seconds"],
            first=schedule_data["seconds"],
            name=name,
            data=data,
            chat_id=chat_id,
        )


async def _run_cron_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    data = context.job.data
    alias, chat_id = data["alias"], data["chat_id"]

    commands = shell_client.load_commands()
    command = commands.get(alias)
    if not command:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ Cron: el alias `{alias}` ya no existe. Elimínalo con `/cron del {data['job_id']}`.",
            parse_mode="Markdown",
        )
        return

    try:
        stdout, stderr, exit_code = await shell_client.run(command)
        output = stdout or stderr or "(sin salida)"
        if len(output) > 3800:
            output = "…\n" + output[-3800:]
        icon = "✅" if exit_code == 0 else "⚠️"
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{icon} *Cron* `{alias}` (exit {exit_code}):\n```\n{output}\n```",
            parse_mode="Markdown",
        )
    except Exception as exc:
        log.exception("Cron job failed for alias=%s", alias)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Error en cron `{alias}`: {exc}",
            parse_mode="Markdown",
        )


def schedule_all(job_queue) -> None:
    """Re-schedule all persisted cron jobs after a bot restart."""
    for job in cron_client.list_all():
        schedule_data = cron_client.parse_schedule(job["schedule"])
        if schedule_data is None:
            log.warning("Horario inválido en cron job %s: %s", job["id"], job["schedule"])
            continue
        _schedule_job(job_queue, job["id"], job["alias"], schedule_data, job["chat_id"])
