# CLAUDE.md

## What this repo is

A Telegram bot for homelab management. Runs as a Docker container on the home server.
See `README.md` for features and user-facing docs.

## Development commands

```bash
pip install -r requirements-dev.txt
pytest                 # run tests
ruff check .           # lint
ruff format .          # format
```

## CI/CD — same pattern as discord-bot

1. **Release published** → `docker-release.yml` builds and pushes to `ghcr.io/enriqueav99/telegram-bot:<version>`
2. → Opens a PR on `enriqueav99/server` bumping `composes/apps/telegram-bot/docker-compose.yaml`
3. → PR auto-merges via `gh pr merge --squash --admin`

The server repo is at `~/server`. The self-hosted GitHub runner (`github-runner` container) executes the workflows.

Relevant secret needed: `SERVER_REPO_PAT` (PAT with `contents:write` + `pull-requests:write` on the server repo).

## Adding a module

1. `modules/<name>_client.py` — pure logic, no Telegram imports
2. `handlers/<name>.py` — handlers decorated with `@require_auth` / `@require_module("name")`
3. Register handlers in `bot.py` (`app.add_handler(...)`)
4. Add feature to `DEFAULT_FEATURES` and `FEATURE_LABELS` in `config.py`

If the module needs jobs re-scheduled on restart (like reminders or cron), add a `schedule_*` function and call it in `main()` after `digest_handler.schedule(...)`.

## Persistent data (data/ directory)

All bot state lives under `data/` (Docker volume). Key files:

| File | Module | Contents |
|---|---|---|
| `data/features.json` | config | Feature flag state |
| `data/shell_commands.json` | shell | Registered command aliases |
| `data/cron_jobs.json` | cron | Scheduled cron jobs |
| `data/reminders.json` | reminders | Pending reminders |
| `data/todos.json` | todo | Task list |
| `data/snippets.json` | snippets | Saved snippets |
| `data/notes.json` | notes | Quick notes |
| `data/alert_history.json` | alerts_history | Last 50 alerts |
| `data/digest.json` | digest | Daily digest schedule |
| `data/claude_history.json` | ask | Claude conversation history |

## Adding a webhook endpoint

The bot runs an aiohttp server alongside the Telegram poller. To add a new webhook source (e.g. Watchtower, Uptime Kuma, Radarr):

1. Write a handler function `async def _my_handler(request) -> web.Response`
2. Register it in `_start_alerts_server()` in `bot.py`: `app.router.add_post("/my-path", _my_handler)`
3. Add the corresponding feature flag in `config.py` so it can be toggled from `/panel`
4. Configure the source app to POST to `http://telegram-bot:9091/my-path` (internal Docker network)

## Integration with server apps

The bot's server-side compose is at `~/server/composes/apps/telegram-bot/docker-compose.yaml`.

**Active integrations:**
| Endpoint | Feature flag | Source app |
|---|---|---|
| `POST /alerts` | `alerts` | Alertmanager (`apps/monitoreo`) |
| `POST /grafana` | `grafana` | Grafana Unified Alerting |
| `POST /radarr` | `radarr` | Radarr (Settings → Connect → Webhook) |
| `POST /sonarr` | `sonarr` | Sonarr (Settings → Connect → Webhook) |
| `POST /crowdsec` | `crowdsec` | CrowdSec HTTP notification plugin |
| Docker socket | `docker` | `/var/run/docker.sock:ro` |

**Native Telegram integrations (bypass the bot's webhook server):**
- **Uptime Kuma** — Settings → Notifications → Telegram (configure via web UI)
- **Watchtower** — set in `apps/watchtower/.env`: `WATCHTOWER_NOTIFICATIONS=telegram`, `WATCHTOWER_NOTIFICATION_TELEGRAM_TOKEN=<bot_token>`, `WATCHTOWER_NOTIFICATION_TELEGRAM_CHAT_ID=<chat_id>`

**Network:**
The bot is in `traefik_proxy`, so it is reachable by container name from any other service on that network (e.g. CrowdSec can POST to `http://telegram-bot:9091/crowdsec`). It can also call internal app APIs (e.g. `http://radarr:7878/api/v3/...`).

## Key files

| File | Purpose |
|---|---|
| `bot.py` | Entry point; wires handlers + aiohttp webhook server; re-schedules reminders/cron on startup |
| `config.py` | `BotConfig` (env) + `FeatureFlags` (persisted in `data/features.json`) |
| `handlers/auth.py` | `@require_auth`, `@require_module` decorators |
| `handlers/reminders.py` | `/remind`, `/reminders`, `/reminddel`; `schedule_pending()` called on startup |
| `handlers/cron.py` | `/cron`; `schedule_all()` called on startup |
| `modules/docker_client.py` | Thin wrapper over the Docker SDK |
| `modules/system_client.py` | psutil-based system metrics |
| `modules/shell_client.py` | Registered command storage + async subprocess execution |
| `modules/cron_client.py` | Cron job storage + schedule string parser (`HH:MM`, `Xm`, `Xh`) |
| `modules/reminder_client.py` | Reminder storage; `list_all_pending()` used on startup |
| `modules/weather_client.py` | wttr.in API client (no API key required) |
| `handlers/calc.py` | Safe AST-based expression evaluator (no `eval`) |
| `healthcheck.py` | Reads `/tmp/.bot_alive` (heartbeat written every 30s) |
