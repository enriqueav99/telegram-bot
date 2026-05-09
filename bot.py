"""Punto de entrada del bot de Telegram para homelab."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from pathlib import Path

from aiohttp import web
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
)

from config import BotConfig, FeatureFlags
from handlers import docker as docker_handler
from handlers import general, panel, webhooks
from handlers import system as system_handler
from logger import start_logger
from modules.docker_client import DockerClient

HEARTBEAT_FILE = Path("/tmp/.bot_alive")
log = logging.getLogger("bot")


async def _start_webhook_server(bot_data: dict, port: int) -> web.AppRunner:
    app = web.Application()
    app["bot_data"] = bot_data
    app.router.add_post("/alerts", webhooks.alertmanager)
    app.router.add_post("/grafana", webhooks.grafana)
    app.router.add_post("/radarr", webhooks.radarr)
    app.router.add_post("/sonarr", webhooks.sonarr)
    app.router.add_post("/crowdsec", webhooks.crowdsec)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    log.info("Servidor webhook escuchando en 0.0.0.0:%d", port)
    return runner


async def main() -> None:
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

    # Start webhook server
    webhook_runner = await _start_webhook_server(bot_data, config.alerts_port)

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
        await webhook_runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Bot detenido")
