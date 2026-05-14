# Bot de Telegram — Homelab

[![Tests](https://github.com/enriqueav99/telegram-bot/actions/workflows/test.yml/badge.svg)](https://github.com/enriqueav99/telegram-bot/actions/workflows/test.yml)
[![Lint](https://github.com/enriqueav99/telegram-bot/actions/workflows/lint.yml/badge.svg)](https://github.com/enriqueav99/telegram-bot/actions/workflows/lint.yml)
[![Docker](https://github.com/enriqueav99/telegram-bot/actions/workflows/docker.yml/badge.svg)](https://github.com/enriqueav99/telegram-bot/actions/workflows/docker.yml)
[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/)

Bot de Telegram en Python para controlar y monitorizar el homelab. Todos los módulos son activables desde `/panel` sin reiniciar.

Usa `/help` en Telegram para ver todos los comandos disponibles.

---

## Características

### Infraestructura

| | |
|---|---|
| 🐳 **Docker Monitor** | Lista contenedores con estado; botones para start/stop/restart y ver logs inline. |
| 📊 **Métricas del sistema** | CPU, RAM, disco, red y uptime en tiempo real vía psutil. Top procesos por CPU/memoria. |
| 🔒 **WireGuard VPN** | Estado de peers: IP, endpoint, último handshake y tráfico. |
| 🔧 **GitHub Actions** | Últimas ejecuciones de workflows con estado y rama. |
| 🖥️ **Comandos del servidor** | Registra y ejecuta comandos shell desde Telegram con captura de salida. |
| ⏱️ **Cron scheduler** | Programa aliases de shell con horario recurrente (`HH:MM`, `Xm`, `Xh`). Persiste entre reinicios. |
| 📋 **Logs** | Navega por logs del servidor (nginx, syslog, auth, docker, kernel) con botones inline. |

### Notificaciones (webhooks entrantes)

| | |
|---|---|
| 🔔 **Alertmanager** | Recibe webhooks de Prometheus Alertmanager y los reenvía al chat. |
| 📈 **Grafana Alerts** | Compatible con Grafana Unified Alerting y formato legacy. |
| 🎬 **Radarr** | Notificaciones de búsqueda, descarga y adición/borrado de películas. |
| 📺 **Sonarr** | Notificaciones de búsqueda, descarga y adición/borrado de series. |
| 🛡️ **CrowdSec** | Alertas del IDS/IPS: IP baneadas con escenario y duración. |
| 🌅 **Resumen diario** | Envía un digest diario con métricas y estado de Docker a la hora configurada. |

### Productividad

| | |
|---|---|
| ⏰ **Recordatorios** | Programar recordatorios con `30m`, `2h`, `1d`, `HH:MM` o fecha exacta. Se reprograman al reiniciar el bot. |
| 📋 **Lista de tareas** | To-do con estados pendiente/hecha, add/done/del. |
| 💾 **Snippets** | Guarda fragmentos de texto o código con nombre; los recupera en bloque de código. |
| 📝 **Notas** | Notas rápidas de texto numeradas. |

### Utilidades

| | |
|---|---|
| 🧮 **Calculadora** | Evalúa expresiones matemáticas de forma segura (sin `eval`). Soporta funciones como `sqrt`, `sin`, `log`. |
| 🌤️ **Tiempo** | Consulta el tiempo de cualquier ciudad vía wttr.in. Temperatura, humedad, viento y previsión de 3 días. |
| 🌐 **Speedtest** | Test de velocidad de internet con descarga, subida y ping. |
| 🧲 **qBittorrent** | Lista torrents activos con progreso; añadir por magnet o URL. |
| 🤖 **Claude (API)** | Asistente de IA con historial de conversación por chat. |

---

## Inicio rápido

```bash
cp .env.example .env   # Rellena TELEGRAM_BOT_TOKEN y ALLOWED_USERS
docker compose up -d --build
```

### Variables de entorno

| Variable | Obligatoria | Descripción |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | Token del bot. Obtenlo con [@BotFather](https://t.me/BotFather). |
| `ALLOWED_USERS` | ✅ | IDs de Telegram separados por comas. Obtén el tuyo con [@userinfobot](https://t.me/userinfobot). |
| `ALERTS_CHAT_ID` | ❌ | Chat ID al que se envían las alertas de Alertmanager/Grafana y el digest diario. |
| `ALERTS_PORT` | ❌ | Puerto del servidor de webhooks (default: `9091`). |
| `LOG_LEVEL` | ❌ | Nivel de log: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`). |
| `GITHUB_TOKEN` | ❌ | PAT de GitHub para el módulo CI (permisos `repo`). |
| `GITHUB_REPO` | ❌ | Repositorio en formato `owner/repo` para el módulo CI. |
| `ANTHROPIC_API_KEY` | ❌ | Clave de la API de Anthropic para el módulo `/ask`. |
| `QBITTORRENT_URL` | ❌ | URL de la WebUI de qBittorrent (ej. `http://qbittorrent:8080`). |
| `QBITTORRENT_USER` | ❌ | Usuario de qBittorrent (default: `admin`). |
| `QBITTORRENT_PASSWORD` | ❌ | Contraseña de qBittorrent. |

---

## Comandos

### Servidor e infraestructura

| Comando | Módulo | Descripción |
|---|---|---|
| `/status` | — | Resumen rápido: CPU/RAM/disco + contenedores activos. |
| `/metrics` | `system` | Métricas detalladas con barras de progreso. |
| `/procs` | `system` | Top 10 procesos por CPU, top 5 por memoria. |
| `/docker` | `docker` | Panel de contenedores con botones start/stop/restart/logs. |
| `/logs` | `ssh` | Navega por los logs del servidor con botones inline. |
| `/wg` | `wireguard` | Estado de peers WireGuard VPN. |
| `/ci` | `github_actions` | Últimas 10 ejecuciones de GitHub Actions. |

### Comandos y cron

| Comando | Módulo | Descripción |
|---|---|---|
| `/cmd` | `shell` | Menú para ejecutar comandos registrados. |
| `/cmdadd <alias> <cmd>` | `shell` | Registra un nuevo alias de comando. |
| `/cmddel <alias>` | `shell` | Elimina un alias. |
| `/restartai` | `shell` | Ejecuta el alias `ai-bot` (reinicia el bot de IA). |
| `/cron add <horario> <alias>` | `cron` | Programa un alias de forma recurrente. |
| `/cron list` | `cron` | Lista los trabajos programados. |
| `/cron del <id>` | `cron` | Elimina un trabajo cron. |

**Formatos de horario para `/cron`:** `HH:MM` (diario a esa hora UTC) · `30m` (cada 30 min) · `6h` (cada 6 horas)

### Recordatorios y productividad

| Comando | Módulo | Descripción |
|---|---|---|
| `/remind <cuándo> <texto>` | `reminders` | Programa un recordatorio. |
| `/reminders` | `reminders` | Lista recordatorios pendientes. |
| `/reminddel <id>` | `reminders` | Cancela un recordatorio. |
| `/todo` | `todo` | Muestra la lista de tareas. |
| `/todo add <texto>` | `todo` | Añade una tarea. |
| `/todo done <id>` | `todo` | Marca una tarea como hecha. |
| `/todo del <id>` | `todo` | Elimina una tarea. |
| `/note <texto>` | `notes` | Guarda una nota rápida. |
| `/note del <id>` | `notes` | Elimina una nota. |
| `/notes` | `notes` | Lista todas las notas. |
| `/snip <nombre> <contenido>` | `snippets` | Guarda un snippet. |
| `/snip <nombre>` | `snippets` | Recupera un snippet. |
| `/snips` | `snippets` | Lista todos los snippets con preview. |
| `/snipdel <nombre>` | `snippets` | Elimina un snippet. |

**Formatos de tiempo para `/remind`:** `30m` · `2h` · `1d` · `14:30` · `2026-06-01 10:00`

### Utilidades

| Comando | Módulo | Descripción |
|---|---|---|
| `/calc <expresión>` | — | Calculadora. Ej: `/calc sqrt(144)`, `/calc sin(pi/2)`. |
| `/weather <ciudad>` | `weather` | Tiempo actual + previsión 3 días. Ej: `/weather Madrid`. |
| `/speedtest` | `speedtest` | Test de velocidad de internet. |
| `/torrents` | `qbittorrent` | Lista torrents activos con progreso. |
| `/torrent <magnet>` | `qbittorrent` | Añade un torrent. |
| `/digest` | `digest` | Ver/cambiar hora del resumen diario (formato `HH:MM` UTC). |
| `/alerts` | — | Historial de las últimas 15 alertas recibidas. |
| `/alertsclear` | — | Limpia el historial de alertas. |

### Asistente

| Comando | Módulo | Descripción |
|---|---|---|
| `/ask <pregunta>` | `ask` | Pregunta al asistente Claude. Mantiene historial por chat. |
| `/askreset` | `ask` | Reinicia la conversación con Claude. |

### General

| Comando | Descripción |
|---|---|
| `/start` | Mensaje de bienvenida. |
| `/help` | Lista completa de comandos. |
| `/panel` | Panel para activar/desactivar módulos. |

---

## Panel de control

`/panel` muestra un teclado inline con todos los módulos. Pulsa para activar o desactivar al momento, sin reiniciar el bot. El estado se persiste en `data/features.json`.

---

## Webhooks

El bot expone un servidor HTTP en `ALERTS_PORT` (default `9091`). Activa el módulo correspondiente desde `/panel` antes de usarlo.

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

**Alerting → Contact points → Add contact point → Webhook**
- URL: `http://telegram-bot:9091/grafana`

### Radarr

**Settings → Connect → Add → Webhook**
- Triggers: `On Grab`, `On Download`, `On Movie Added`, `On Movie Delete`
- URL: `http://telegram-bot:9091/radarr`

### Sonarr

**Settings → Connect → Add → Webhook**
- Triggers: `On Grab`, `On Download`, `On Series Add`, `On Series Delete`
- URL: `http://telegram-bot:9091/sonarr`

### CrowdSec

```yaml
# /etc/crowdsec/notifications/http.yaml
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

### Watchtower (nativo)

```env
# composes/apps/watchtower/.env
WATCHTOWER_NOTIFICATIONS=telegram
WATCHTOWER_NOTIFICATION_TELEGRAM_TOKEN=<bot_token>
WATCHTOWER_NOTIFICATION_TELEGRAM_CHAT_ID=<chat_id>
```

### Uptime Kuma (nativo)

**Settings → Notifications → Add Notification → Telegram.** Introduce el bot token y el chat ID.

---

## Arquitectura

```
telegram-bot/
├── bot.py                      # Entry point + servidor webhook (aiohttp)
├── config.py                   # BotConfig (env vars) + FeatureFlags (data/features.json)
├── logger.py
├── healthcheck.py              # Healthcheck via heartbeat en /tmp/.bot_alive
├── modules/
│   ├── docker_client.py        # Wrapper del Docker SDK
│   ├── system_client.py        # Métricas del sistema con psutil
│   ├── shell_client.py         # Ejecución y registro de comandos shell
│   ├── cron_client.py          # Persistencia y parsing de trabajos cron
│   ├── reminder_client.py      # Persistencia de recordatorios
│   ├── todo_client.py          # Persistencia de lista de tareas
│   ├── snippets_client.py      # Persistencia de snippets
│   ├── notes_client.py         # Persistencia de notas
│   ├── alert_history.py        # Historial de alertas (max 50)
│   ├── weather_client.py       # Consulta wttr.in
│   ├── speedtest_client.py     # Wrapper de speedtest-cli
│   ├── qbittorrent_client.py   # Cliente WebAPI de qBittorrent
│   ├── claude_client.py        # Cliente de la API de Anthropic
│   ├── github_client.py        # Cliente de la API de GitHub
│   └── wireguard_client.py     # Parser de `wg show all dump`
├── handlers/
│   ├── auth.py                 # Decoradores @require_auth y @require_module
│   ├── general.py              # /start, /help, /status
│   ├── panel.py                # /panel + callbacks de toggle
│   ├── docker.py               # /docker + callbacks de contenedores
│   ├── system.py               # /metrics, /procs
│   ├── shell.py                # /cmd, /cmdadd, /cmddel, /restartai
│   ├── cron.py                 # /cron
│   ├── reminders.py            # /remind, /reminders, /reminddel
│   ├── todo.py                 # /todo
│   ├── snippets.py             # /snip, /snips, /snipdel
│   ├── notes.py                # /note, /notes
│   ├── calc.py                 # /calc
│   ├── weather.py              # /weather
│   ├── speedtest.py            # /speedtest
│   ├── qbittorrent.py          # /torrents, /torrent
│   ├── ask.py                  # /ask, /askreset
│   ├── digest.py               # /digest + job diario
│   ├── logs.py                 # /logs + callbacks
│   ├── wireguard.py            # /wg + callbacks
│   ├── github.py               # /ci + callbacks
│   ├── alerts_history.py       # /alerts, /alertsclear
│   └── webhooks.py             # Handlers HTTP: alertmanager, grafana, radarr, sonarr, crowdsec
└── tests/
    ├── test_config.py
    ├── test_auth.py
    ├── test_docker_client.py
    ├── test_system_client.py
    └── test_webhooks.py
```

### Datos persistentes

Todos los datos del bot se guardan en `data/` (montado como volumen en Docker):

| Archivo | Contenido |
|---|---|
| `data/features.json` | Estado de los feature flags |
| `data/shell_commands.json` | Aliases de comandos shell |
| `data/cron_jobs.json` | Trabajos cron programados |
| `data/reminders.json` | Recordatorios pendientes |
| `data/todos.json` | Lista de tareas |
| `data/snippets.json` | Snippets guardados |
| `data/notes.json` | Notas |
| `data/alert_history.json` | Historial de alertas (max 50) |
| `data/digest.json` | Hora del resumen diario |
| `data/claude_history.json` | Historial de conversaciones con Claude |

---

## Integración con el repo server

Al publicar un release, el workflow `docker-release` sube la imagen a GHCR y abre automáticamente una PR en [`enriqueav99/server`](https://github.com/enriqueav99/server) para actualizar el tag en `composes/apps/telegram-bot/docker-compose.yaml`.

Requiere el secret `SERVER_REPO_PAT` (PAT con `contents:write` y `pull-requests:write` sobre el repo server).

---

## Desarrollo

```bash
pip install -r requirements-dev.txt
pytest           # Tests
ruff check .     # Lint
ruff format .    # Formato
```

Para añadir un módulo nuevo, sigue el patrón en `CLAUDE.md`.
