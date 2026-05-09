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
| `bot.py` | Entry point; wires handlers + aiohttp webhook server |
| `config.py` | `BotConfig` (env) + `FeatureFlags` (persisted in `data/features.json`) |
| `handlers/auth.py` | `@require_auth`, `@require_module` decorators |
| `modules/docker_client.py` | Thin wrapper over the Docker SDK |
| `modules/system_client.py` | psutil-based system metrics |
| `healthcheck.py` | Reads `/tmp/.bot_alive` (heartbeat written every 30s) |
