# Bot de Telegram — Homelab

[![Tests](https://github.com/enriqueav99/telegram-bot/actions/workflows/test.yml/badge.svg)](https://github.com/enriqueav99/telegram-bot/actions/workflows/test.yml)
[![Lint](https://github.com/enriqueav99/telegram-bot/actions/workflows/lint.yml/badge.svg)](https://github.com/enriqueav99/telegram-bot/actions/workflows/lint.yml)
[![Docker](https://github.com/enriqueav99/telegram-bot/actions/workflows/docker.yml/badge.svg)](https://github.com/enriqueav99/telegram-bot/actions/workflows/docker.yml)
[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/)

Bot de Telegram en Python para controlar y monitorizar el homelab. Se integra con Docker, métricas del sistema y el stack de Alertmanager.

Usa `/help` en Telegram para ver todos los comandos disponibles.

---

## Características

| | |
|---|---|
| 🐳 **Docker Monitor** | Lista todos los contenedores con su estado, y permite hacer start/stop/restart y ver logs directamente desde Telegram con botones inline. |
| 📊 **Métricas del sistema** | CPU, RAM, disco y uptime con barra de progreso visual. Datos en tiempo real vía psutil. |
| 🔔 **Alertmanager** | Endpoint HTTP que recibe webhooks de Prometheus Alertmanager y reenvía las alertas al chat configurado. |
| 📈 **Grafana Alerts** | Endpoint HTTP para Grafana Unified Alerting (y formato legacy). Compatible con el mismo `ALERTS_CHAT_ID`. |
| 🎬 **Radarr** | Notificaciones de búsqueda, descarga y adición de películas vía webhook. |
| 📺 **Sonarr** | Notificaciones de búsqueda, descarga y adición de series vía webhook. |
| 🛡️ **CrowdSec** | Alertas de seguridad del IDS/IPS: IP baneadas con escenario y duración. |
| 🤖 **Panel de control** | Activa o desactiva cualquier módulo desde el propio chat sin reiniciar el bot. El estado se persiste en disco. |
| 🔒 **Seguridad** | Whitelist de usuarios por ID de Telegram. Sin whitelist configurada, el bot rechaza a cualquier usuario desconocido. |

---

## Inicio rápido

```bash
cp .env.example .env   # Rellena TELEGRAM_BOT_TOKEN y ALLOWED_USERS
docker compose up -d --build
```

### Variables de entorno

| Variable | Obligatoria | Descripción |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | Token del bot. Obtenlo hablando con [@BotFather](https://t.me/BotFather). |
| `ALLOWED_USERS` | ✅ | IDs de Telegram separados por comas. Obtén el tuyo con [@userinfobot](https://t.me/userinfobot). |
| `ALERTS_CHAT_ID` | ❌ | Chat ID al que se envían las alertas de Alertmanager (puede ser tu ID personal o un grupo). |
| `ALERTS_PORT` | ❌ | Puerto del servidor de alertas (default: `9091`). |
| `LOG_LEVEL` | ❌ | Nivel de log: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`). |

---

## Comandos

| Comando | Módulo | Descripción |
|---|---|---|
| `/start` | — | Mensaje de bienvenida. |
| `/help` | — | Lista de comandos disponibles. |
| `/status` | — | Resumen rápido: CPU/RAM/uptime + nº de contenedores activos. |
| `/panel` | — | Panel de control para activar o desactivar módulos. |
| `/metrics` | `system` | Métricas detalladas del sistema con barras de progreso. |
| `/docker` | `docker` | Lista de contenedores con botones para start/stop/restart/logs. |

---

## Panel de control

El comando `/panel` muestra un teclado inline con todos los módulos. Pulsa un botón para activarlo o desactivarlo al momento, sin necesidad de reiniciar el bot.

```
🤖 Panel de Control del Homelab

Activa o desactiva los módulos:

  ✅ 🐳 Docker Monitor — activado
  ✅ 📊 Métricas del sistema — activado
  ❌ 🔔 Alertmanager — desactivado

[✅ 🐳 Docker Monitor      ]
[✅ 📊 Métricas del sistema]
[❌ 🔔 Alertmanager        ]
[🔄 Actualizar             ]
```

---

## Webhooks

El bot expone un servidor HTTP en el puerto configurado (`ALERTS_PORT`, default `9091`). Activa cada módulo desde `/panel` antes de usarlo. Todos los mensajes se envían al chat configurado en `ALERTS_CHAT_ID`.

### Alertmanager

```yaml
# alertmanager.yml
receivers:
  - name: telegram
    webhook_configs:
      - url: "http://telegram-bot:9091/alerts"
        send_resolved: true
```

### Grafana

En Grafana: **Alerting → Contact points → Add contact point → Webhook**

- URL: `http://telegram-bot:9091/grafana`
- Compatible con Unified Alerting y el formato legacy.

### Radarr

En Radarr: **Settings → Connect → Add → Webhook**

- Notification Triggers: `On Grab`, `On Download`, `On Movie Added`, `On Movie Delete`
- URL: `http://telegram-bot:9091/radarr`

### Sonarr

En Sonarr: **Settings → Connect → Add → Webhook**

- Notification Triggers: `On Grab`, `On Download`, `On Series Add`, `On Series Delete`
- URL: `http://telegram-bot:9091/sonarr`

### CrowdSec

En `/etc/crowdsec/notifications/http.yaml`:

```yaml
type: http
name: telegram_bot
log_level: info
format: |
  {{range .}}{"scenario": "{{.Scenario}}", "source": {"ip": "{{.Source.IP}}", "as_name": "{{.Source.AsName}}"}, "decisions": [{{range .Decisions}}{"type": "{{.Type}}", "duration": "{{.Duration}}"}{{end}}]}
  {{end}}
url: http://telegram-bot:9091/crowdsec
method: POST
headers:
  Content-Type: application/json
```

Activa el notifier en `/etc/crowdsec/profiles.yaml`.

### Watchtower (nativo)

Watchtower envía las notificaciones directamente a Telegram sin pasar por el webhook del bot. Añade en `composes/apps/watchtower/.env`:

```env
WATCHTOWER_NOTIFICATIONS=telegram
WATCHTOWER_NOTIFICATION_TELEGRAM_TOKEN=<tu_bot_token>
WATCHTOWER_NOTIFICATION_TELEGRAM_CHAT_ID=<chat_id>
```

### Uptime Kuma (nativo)

En Uptime Kuma: **Settings → Notifications → Add Notification → Telegram**. Introduce el bot token y el chat ID.

---

## Arquitectura

```
telegram-bot/
├── bot.py                  # Entry point + servidor webhook (aiohttp)
├── config.py               # BotConfig (env vars) + FeatureFlags (data/features.json)
├── logger.py
├── healthcheck.py          # Healthcheck via heartbeat en /tmp/.bot_alive
├── modules/
│   ├── docker_client.py    # Wrapper del Docker SDK
│   └── system_client.py    # Métricas del sistema con psutil
├── handlers/
│   ├── auth.py             # Decoradores @require_auth y @require_module
│   ├── general.py          # /start, /help, /status
│   ├── panel.py            # /panel + callbacks de toggle
│   ├── docker.py           # /docker + callbacks de contenedores
│   ├── system.py           # /metrics
│   └── webhooks.py         # Handlers HTTP: alertmanager, grafana, radarr, sonarr, crowdsec
└── tests/
    ├── test_config.py
    ├── test_auth.py
    ├── test_docker_client.py
    ├── test_system_client.py
    └── test_webhooks.py
```

El bot monta el socket de Docker en **read-only** (`/var/run/docker.sock:ro`). Si necesitas start/stop/restart elimina el `:ro` del `docker-compose.yaml`.

---

## Integración con el repo server

Al publicar un release en este repo, el workflow `docker-release` sube la imagen a GHCR y abre automáticamente una PR en [`enriqueav99/server`](https://github.com/enriqueav99/server) para actualizar el tag en `composes/apps/telegram-bot/docker-compose.yaml`.

Para que funcione necesitas:

1. Crear el secret `SERVER_REPO_PAT` en este repo (un PAT con permisos `contents:write` y `pull-requests:write` sobre el repo server).
2. Que exista `composes/apps/telegram-bot/docker-compose.yaml` en el repo server con una línea `image: ghcr.io/enriqueav99/telegram-bot:<version>`.

---

## Desarrollo

```bash
pip install -r requirements-dev.txt
pytest           # Tests
ruff check .     # Lint
ruff format .    # Formato
```

Para añadir un módulo nuevo:

1. Crea la lógica en `modules/mi_modulo.py`.
2. Añade el handler en `handlers/mi_handler.py` usando `@require_auth` y `@require_module("mi_modulo")`.
3. Registra el `CommandHandler` en `bot.py`.
4. Añade la feature a `DEFAULT_FEATURES` y `FEATURE_LABELS` en `config.py`.
