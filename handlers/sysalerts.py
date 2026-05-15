from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from handlers.auth import require_auth, require_module
from modules.sysalert_client import METRICS, SysAlertClient

log = logging.getLogger(__name__)

_LABELS = {"cpu": "CPU", "ram": "RAM", "disco": "disk", "disk": "disk"}
_ICONS = {"cpu": "🖥️", "ram": "💾", "disk": "💿"}


def _metric_alias(raw: str) -> str | None:
    """Normalize metric name; accept 'disco' as alias for 'disk'."""
    return _LABELS.get(raw.lower())


@require_auth
@require_module("sysalerts")
async def sysalert_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client: SysAlertClient = context.bot_data["sysalerts"]

    if not context.args:
        thresholds = client.all_thresholds()
        lines = ["🔔 *Alertas de sistema*\n"]
        for m in METRICS:
            icon = _ICONS[m]
            val = thresholds[m]
            status = f"{val:.0f}%" if val is not None else "desactivada"
            firing = " ⚠️ *ACTIVA*" if client.is_firing(m) else ""
            lines.append(f"{icon} *{m.upper()}*: umbral {status}{firing}")
        lines.append("\n_Uso: `/sysalert cpu 85` · `/sysalert cpu off`_")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Uso: `/sysalert <métrica> <umbral|off>`\nMétricas: `cpu`, `ram`, `disk`",
            parse_mode="Markdown",
        )
        return

    raw_metric, raw_value = context.args[0], context.args[1]
    metric = _metric_alias(raw_metric)
    if metric is None:
        await update.message.reply_text(
            "Métrica no reconocida. Usa: `cpu`, `ram`, `disk`", parse_mode="Markdown"
        )
        return

    if raw_value.lower() == "off":
        client.set_threshold(metric, None)
        await update.message.reply_text(
            f"✅ Alerta de *{metric.upper()}* desactivada", parse_mode="Markdown"
        )
        return

    try:
        value = float(raw_value)
        if not (0 < value < 100):
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "El umbral debe ser un número entre 1 y 99.", parse_mode="Markdown"
        )
        return

    client.set_threshold(metric, value)
    await update.message.reply_text(
        f"✅ Umbral de *{metric.upper()}* configurado a *{value:.0f}%*",
        parse_mode="Markdown",
    )


async def check_sysalerts(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Periodic job: query Prometheus and fire onset/recovery alerts."""
    features = context.bot_data["features"]
    config = context.bot_data["config"]
    client: SysAlertClient = context.bot_data["sysalerts"]
    prom = context.bot_data.get("prometheus")

    if not features.is_enabled("sysalerts"):
        return
    if prom is None or not prom.available:
        return
    if not config.alerts_chat_id:
        return

    values = await _fetch_metrics(prom)

    for metric, current in values.items():
        threshold = client.get_threshold(metric)
        if threshold is None or current is None:
            continue

        was_firing = client.is_firing(metric)
        now_firing = current >= threshold

        if now_firing and not was_firing:
            client.set_firing(metric, True)
            icon = _ICONS[metric]
            await context.bot.send_message(
                chat_id=config.alerts_chat_id,
                text=(
                    f"🚨 *Alerta de sistema — {metric.upper()}*\n\n"
                    f"{icon} {metric.upper()}: *{current:.1f}%* ≥ umbral {threshold:.0f}%"
                ),
                parse_mode="Markdown",
            )
        elif was_firing and not now_firing:
            client.set_firing(metric, False)
            icon = _ICONS[metric]
            await context.bot.send_message(
                chat_id=config.alerts_chat_id,
                text=(
                    f"✅ *Recuperado — {metric.upper()}*\n\n"
                    f"{icon} {metric.upper()}: *{current:.1f}%* < umbral {threshold:.0f}%"
                ),
                parse_mode="Markdown",
            )


async def _fetch_metrics(prom) -> dict[str, float | None]:
    import asyncio

    cpu, ram, disk = await asyncio.gather(
        prom.query('100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'),
        prom.query("100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)"),
        prom.query(
            '100 * (1 - node_filesystem_avail_bytes{mountpoint="/",fstype!~"tmpfs|rootfs|overlay"}'
            ' / node_filesystem_size_bytes{mountpoint="/",fstype!~"tmpfs|rootfs|overlay"})'
        ),
    )
    return {"cpu": cpu, "ram": ram, "disk": disk}
