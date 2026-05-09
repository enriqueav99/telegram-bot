"""Webhook handlers for external service integrations."""

from __future__ import annotations

import contextlib
import logging

from aiohttp import web
from telegram import Bot

from config import BotConfig, FeatureFlags

log = logging.getLogger(__name__)


async def _send(bot: Bot, chat_id: int, text: str) -> None:
    with contextlib.suppress(Exception):
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")


async def alertmanager(request: web.Request) -> web.Response:
    bot_data = request.app["bot_data"]
    features: FeatureFlags = bot_data["features"]
    bot: Bot = bot_data["bot"]
    config: BotConfig = bot_data["config"]

    if not features.is_enabled("alerts"):
        return web.Response(status=200, text="alerts module disabled")
    if not config.alerts_chat_id:
        return web.Response(status=200, text="no chat_id configured")

    try:
        body = await request.json()
    except Exception:
        return web.Response(status=400, text="invalid json")

    for alert in body.get("alerts", []):
        status = alert.get("status", "unknown").upper()
        name = alert.get("labels", {}).get("alertname", "sin nombre")
        severity = alert.get("labels", {}).get("severity", "")
        summary = alert.get("annotations", {}).get("summary", "")
        description = alert.get("annotations", {}).get("description", "")

        icon = "🔴" if status == "FIRING" else "🟢"
        sev_icon = "⚠️" if severity == "warning" else ("🚨" if severity == "critical" else "ℹ️")

        lines = [f"{icon} {sev_icon} *{name}* — {status}"]
        if summary:
            lines.append(f"_{summary}_")
        if description:
            lines.append(description)

        await _send(bot, config.alerts_chat_id, "\n".join(lines))

    return web.Response(status=200, text="ok")


async def grafana(request: web.Request) -> web.Response:
    """Handles both Grafana Unified Alerting and legacy webhook formats."""
    bot_data = request.app["bot_data"]
    features: FeatureFlags = bot_data["features"]
    bot: Bot = bot_data["bot"]
    config: BotConfig = bot_data["config"]

    if not features.is_enabled("grafana"):
        return web.Response(status=200, text="grafana module disabled")
    if not config.alerts_chat_id:
        return web.Response(status=200, text="no chat_id configured")

    try:
        body = await request.json()
    except Exception:
        return web.Response(status=400, text="invalid json")

    alerts = body.get("alerts", [])
    if alerts:
        for alert in alerts:
            status = alert.get("status", "unknown").upper()
            name = alert.get("labels", {}).get("alertname", "sin nombre")
            severity = alert.get("labels", {}).get("severity", "")
            summary = alert.get("annotations", {}).get("summary", "")
            description = alert.get("annotations", {}).get("description", "")

            icon = "🔴" if status == "FIRING" else "🟢"
            sev_icon = "⚠️" if severity == "warning" else ("🚨" if severity == "critical" else "ℹ️")

            lines = [f"📈 {icon} {sev_icon} *{name}* — {status}"]
            if summary:
                lines.append(f"_{summary}_")
            if description:
                lines.append(description)

            await _send(bot, config.alerts_chat_id, "\n".join(lines))
    else:
        title = body.get("title", "Alerta de Grafana")
        message = body.get("message", "")
        state = body.get("state", "unknown")
        icon = "🔴" if state == "alerting" else "🟢"
        lines = [f"📈 {icon} *{title}*"]
        if message:
            lines.append(message)
        await _send(bot, config.alerts_chat_id, "\n".join(lines))

    return web.Response(status=200, text="ok")


async def radarr(request: web.Request) -> web.Response:
    bot_data = request.app["bot_data"]
    features: FeatureFlags = bot_data["features"]
    bot: Bot = bot_data["bot"]
    config: BotConfig = bot_data["config"]

    if not features.is_enabled("radarr"):
        return web.Response(status=200, text="radarr module disabled")
    if not config.alerts_chat_id:
        return web.Response(status=200, text="no chat_id configured")

    try:
        body = await request.json()
    except Exception:
        return web.Response(status=400, text="invalid json")

    event = body.get("eventType", "")
    movie = body.get("movie", {})
    title = movie.get("title", "desconocida")
    year = movie.get("year", "")
    title_year = f"{title} ({year})" if year else title

    if event == "Test":
        await _send(bot, config.alerts_chat_id, "🎬 Radarr: conexión establecida correctamente")
    elif event == "Grab":
        quality = body.get("release", {}).get("quality", "")
        msg = f"🎬 Radarr: buscando *{title_year}*"
        if quality:
            msg += f" — {quality}"
        await _send(bot, config.alerts_chat_id, msg)
    elif event == "Download":
        movie_file = body.get("movieFile", body.get("release", {}))
        quality = movie_file.get("quality", "")
        icon = "⬆️" if body.get("isUpgrade", False) else "✅"
        msg = f"{icon} Radarr: *{title_year}* descargada"
        if quality:
            msg += f" — {quality}"
        await _send(bot, config.alerts_chat_id, msg)
    elif event == "MovieAdded":
        await _send(
            bot, config.alerts_chat_id, f"🎬 Radarr: *{title_year}* añadida a la biblioteca"
        )
    elif event == "MovieDeleted":
        await _send(
            bot, config.alerts_chat_id, f"🗑️ Radarr: *{title_year}* eliminada de la biblioteca"
        )
    else:
        log.debug("Radarr: evento ignorado '%s'", event)

    return web.Response(status=200, text="ok")


async def sonarr(request: web.Request) -> web.Response:
    bot_data = request.app["bot_data"]
    features: FeatureFlags = bot_data["features"]
    bot: Bot = bot_data["bot"]
    config: BotConfig = bot_data["config"]

    if not features.is_enabled("sonarr"):
        return web.Response(status=200, text="sonarr module disabled")
    if not config.alerts_chat_id:
        return web.Response(status=200, text="no chat_id configured")

    try:
        body = await request.json()
    except Exception:
        return web.Response(status=400, text="invalid json")

    event = body.get("eventType", "")
    series_title = body.get("series", {}).get("title", "desconocida")
    episodes = body.get("episodes", [])

    def _ep_str(ep: dict) -> str:
        s = ep.get("seasonNumber", "?")
        e = ep.get("episodeNumber", "?")
        label = f"S{s:02d}E{e:02d}" if isinstance(s, int) and isinstance(e, int) else f"S{s}E{e}"
        ep_title = ep.get("title", "")
        return f"{label} — {ep_title}" if ep_title else label

    if event == "Test":
        await _send(bot, config.alerts_chat_id, "📺 Sonarr: conexión establecida correctamente")
    elif event == "Grab":
        quality = body.get("release", {}).get("quality", "")
        ep_list = ", ".join(_ep_str(e) for e in episodes[:3])
        msg = f"📺 Sonarr: buscando *{series_title}*"
        if ep_list:
            msg += f" {ep_list}"
        if quality:
            msg += f" — {quality}"
        await _send(bot, config.alerts_chat_id, msg)
    elif event == "Download":
        ep_file = body.get("episodeFile", body.get("release", {}))
        quality = ep_file.get("quality", "")
        icon = "⬆️" if body.get("isUpgrade", False) else "✅"
        ep_list = ", ".join(_ep_str(e) for e in episodes[:3])
        msg = f"{icon} Sonarr: *{series_title}*"
        if ep_list:
            msg += f" {ep_list}"
        if quality:
            msg += f" — {quality}"
        await _send(bot, config.alerts_chat_id, msg)
    elif event == "SeriesAdd":
        await _send(
            bot, config.alerts_chat_id, f"📺 Sonarr: *{series_title}* añadida a la biblioteca"
        )
    elif event == "SeriesDelete":
        await _send(
            bot, config.alerts_chat_id, f"🗑️ Sonarr: *{series_title}* eliminada de la biblioteca"
        )
    else:
        log.debug("Sonarr: evento ignorado '%s'", event)

    return web.Response(status=200, text="ok")


async def crowdsec(request: web.Request) -> web.Response:
    bot_data = request.app["bot_data"]
    features: FeatureFlags = bot_data["features"]
    bot: Bot = bot_data["bot"]
    config: BotConfig = bot_data["config"]

    if not features.is_enabled("crowdsec"):
        return web.Response(status=200, text="crowdsec module disabled")
    if not config.alerts_chat_id:
        return web.Response(status=200, text="no chat_id configured")

    try:
        body = await request.json()
    except Exception:
        return web.Response(status=400, text="invalid json")

    alerts = body if isinstance(body, list) else body.get("alerts", [])

    for alert in alerts[:10]:
        scenario = alert.get("scenario", "unknown")
        source = alert.get("source", {})
        ip = source.get("ip", source.get("value", "?"))
        as_name = source.get("as_name", "")
        decisions = alert.get("decisions", [])

        lines = [f"🛡️ *CrowdSec* — `{ip}`"]
        if as_name:
            lines.append(f"ASN: {as_name}")
        lines.append(f"Escenario: `{scenario}`")
        for d in decisions[:3]:
            lines.append(f"Acción: {d.get('type', '')} ({d.get('duration', '')})")

        await _send(bot, config.alerts_chat_id, "\n".join(lines))

    return web.Response(status=200, text="ok")
