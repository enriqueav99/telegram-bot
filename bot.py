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
from handlers import alerts_history as alerts_history_handler
from handlers import ask as ask_handler
from handlers import digest as digest_handler
from handlers import docker as docker_handler
from handlers import general, notes, panel, webhooks
from handlers import github as github_handler
from handlers import logs as logs_handler
from handlers import qbittorrent as qbt_handler
from handlers import speedtest as speedtest_handler
from handlers import ssh as ssh_handler
from handlers import system as system_handler
from handlers import wireguard as wireguard_handler
from logger import start_logger
from modules.claude_client import ClaudeClient
from modules.docker_client import DockerClient
from modules.github_client import GitHubClient
from modules.qbittorrent_client import QBittorrentClient

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
    qbt = QBittorrentClient()
    claude = ClaudeClient()
    github = GitHubClient(config.github_token, config.github_repo)

    app = Application.builder().token(config.token).build()

    bot_data = {
        "config": config,
        "features": features,
        "docker": docker,
        "bot": app.bot,
        "qbt": qbt,
        "claude": claude,
        "github": github,
    }
    app.bot_data.update(bot_data)

    # Commands
    app.add_handler(CommandHandler("start", general.start))
    app.add_handler(CommandHandler("help", general.help_cmd))
    app.add_handler(CommandHandler("status", general.status))
    app.add_handler(CommandHandler("metrics", system_handler.metrics))
    app.add_handler(CommandHandler("docker", docker_handler.docker_list))
    app.add_handler(CommandHandler("panel", panel.panel))
    app.add_handler(CommandHandler("speedtest", speedtest_handler.speedtest_cmd))
    app.add_handler(CommandHandler("note", notes.note_cmd))
    app.add_handler(CommandHandler("notes", notes.notes_list))
    app.add_handler(CommandHandler("digest", digest_handler.digest_cmd))
    app.add_handler(CommandHandler("torrents", qbt_handler.torrents_cmd))
    app.add_handler(CommandHandler("torrent", qbt_handler.torrent_add))
    app.add_handler(CommandHandler("ssh", ssh_handler.ssh_cmd))
    app.add_handler(CommandHandler("sshadd", ssh_handler.sshadd_cmd))
    app.add_handler(CommandHandler("sshdel", ssh_handler.sshdel_cmd))
    app.add_handler(CommandHandler("restartai", ssh_handler.restartai_cmd))
    app.add_handler(CommandHandler("procs", system_handler.procs))
    app.add_handler(CommandHandler("logs", logs_handler.logs_cmd))
    app.add_handler(CommandHandler("alerts", alerts_history_handler.alerts_cmd))
    app.add_handler(CommandHandler("alertsclear", alerts_history_handler.alerts_clear))
    app.add_handler(CommandHandler("ask", ask_handler.ask_cmd))
    app.add_handler(CommandHandler("askreset", ask_handler.ask_reset))
    app.add_handler(CommandHandler("wg", wireguard_handler.wg_cmd))
    app.add_handler(CommandHandler("ci", github_handler.ci_cmd))

    # Callbacks
    app.add_handler(CallbackQueryHandler(panel.panel_callback, pattern=r"^panel:"))
    app.add_handler(CallbackQueryHandler(docker_handler.docker_callback, pattern=r"^docker:"))
    app.add_handler(CallbackQueryHandler(qbt_handler.qbt_callback, pattern=r"^qbt:"))
    app.add_handler(CallbackQueryHandler(ssh_handler.ssh_callback, pattern=r"^ssh:"))
    app.add_handler(CallbackQueryHandler(logs_handler.logs_callback, pattern=r"^logs:"))
    app.add_handler(CallbackQueryHandler(wireguard_handler.wg_callback, pattern=r"^wg:"))
    app.add_handler(CallbackQueryHandler(github_handler.ci_callback, pattern=r"^ci:"))

    # Heartbeat
    async def heartbeat(_: object) -> None:
        with contextlib.suppress(OSError):
            HEARTBEAT_FILE.write_text(str(int(time.time())))

    app.job_queue.run_repeating(heartbeat, interval=30, first=0)

    # Schedule daily digest
    digest_hour, digest_minute = digest_handler.load_config()
    digest_handler.schedule(app.job_queue, digest_hour, digest_minute)

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
