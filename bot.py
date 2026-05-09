"""Punto de entrada del bot de Telegram para homelab."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from pathlib import Path

from aiohttp import web
from telegram import Bot
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
)

from config import BotConfig, FeatureFlags
from handlers import docker as docker_handler
from handlers import general, panel
from handlers import system as system_handler
from logger import start_logger
from modules.docker_client import DockerClient

HEARTBEAT_FILE = Path("/tmp/.bot_alive")
log = logging.getLogger("bot")


async def _alertmanager_handler(request: web.Request) -> web.Response:
    """Recibe webhooks de Alertmanager y los reenvía al chat configurado."""
    app_data = request.app["bot_data"]
    features: FeatureFlags = app_data["features"]
    bot: Bot = app_data["bot"]
    config: BotConfig = app_data["config"]

    if not features.is_enabled("alerts"):
        return web.Response(status=200, text="alerts module disabled")

    if not config.alerts_chat_id:
        return web.Response(status=200, text="no chat_id configured")

    try:
        body = await request.json()
    except Exception:
        return web.Response(status=400, text="invalid json")

    alerts = body.get("alerts", [])
    for alert in alerts:
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

        with contextlib.suppress(Exception):
            await bot.send_message(
                chat_id=config.alerts_chat_id,
                text="\n".join(lines),
                parse_mode="Markdown",
            )

    return web.Response(status=200, text="ok")


async def _start_alerts_server(bot_data: dict, port: int) -> web.AppRunner:
    app = web.Application()
    app["bot_data"] = bot_data
    app.router.add_post("/alerts", _alertmanager_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    log.info("Servidor de alertas escuchando en 0.0.0.0:%d/alerts", port)
    return runner


async def main() -> None:
    start_logger()

    config = BotConfig.load()
    start_logger(config.log_level)

    features = FeatureFlags()
    docker = DockerClient()

    app = Application.builder().token(config.token).build()

    bot_data = {
        "config": config,
        "features": features,
        "docker": docker,
        "bot": app.bot,
    }
    app.bot_data.update(bot_data)

    # Commands
    app.add_handler(CommandHandler("start", general.start))
    app.add_handler(CommandHandler("help", general.help_cmd))
    app.add_handler(CommandHandler("status", general.status))
    app.add_handler(CommandHandler("metrics", system_handler.metrics))
    app.add_handler(CommandHandler("docker", docker_handler.docker_list))
    app.add_handler(CommandHandler("panel", panel.panel))

    # Callbacks
    app.add_handler(CallbackQueryHandler(panel.panel_callback, pattern=r"^panel:"))
    app.add_handler(CallbackQueryHandler(docker_handler.docker_callback, pattern=r"^docker:"))

    # Heartbeat
    async def heartbeat(_: object) -> None:
        with contextlib.suppress(OSError):
            HEARTBEAT_FILE.write_text(str(int(time.time())))

    app.job_queue.run_repeating(heartbeat, interval=30, first=0)

    # Start alerts webhook server
    alerts_runner = await _start_alerts_server(bot_data, config.alerts_port)

    log.info("Bot iniciado")
    try:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        await alerts_runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Bot detenido")
