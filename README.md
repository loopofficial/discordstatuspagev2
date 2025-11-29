# Discord Service Monitor Bot

Monitor websites and servers from Discord with a live status dashboard, incident reporting, and alerts.

## Features
- Live dashboard: One embed updated in-place with service status, latency, and downtime.
- Incidents: Auto-created when services go down; shows downtime on recovery; clear via button.
- Alerts: Clean `@everyone` ping and DMs to a specific role (skips bots and users with DMs off).
- Config-driven: `.env` for secrets, `config.py` for services and thresholds.
- No legacy prefix commands: operation is fully automatic (dashboard + incidents). Slash commands can be added for interactive configuration.

## Requirements
- Python 3.8+
- Discord bot permissions: Send Messages, Embed Links, Manage Messages, Read Message History
- Enable privileged intents in Developer Portal:
	- Server Members Intent
	- Message Content Intent

## Setup (Windows PowerShell)
```powershell
git clone https://github.com/loopofficial/discordstatuspage.git
cd discordstatuspage

python -m venv venv
./venv/Scripts/Activate.ps1
pip install -r requirements.txt

Set-Content -Path .env -Value @"
DISCORD_TOKEN=
"@

python main.py
```

When the bot starts and is invited:
1. Use `/setup` to set the status channel, alert channel, and alert role (dashboard updates are paused until this is done).
2. Add monitoring targets with `/addwebsite` and `/addserver`.
3. Adjust thresholds with `/setlatency` as needed.
4. View current config via `/listservices`.
5. Use `/reload` after manual file edits (rarely needed).

## Runtime Configuration
Most configuration is done with slash commands (requires "Manage Server" permission):

- `/setup status_channel:<channel> alert_channel:<channel> alert_role:<name>` – initial setup
- `/addwebsite url:<https://...>` – monitor a website (expects HTTP 200)
- `/removewebsite url:<https://...>` – stop monitoring a website
- `/addserver name:<label> host:<ip-or-host> [latency_threshold:<ms>]` – monitor a host via ping
- `/removeserver name:<label>` – stop monitoring a server
- `/setlatency service_name:<name> threshold:<ms>` – override latency threshold
- `/listservices` – view current monitored items and thresholds
- `/reload` – reapply persisted runtime config (rarely needed)

Persistent data is stored in `data/runtime_config.json` and applied automatically on startup.
Static defaults in `config.py` remain empty; rely on commands instead.

## Monitoring Settings
- `ping_attempts` (default 3)
- `ping_delay` seconds (0.5)
- `http_timeout` seconds (5)
- `failure_threshold` consecutive failures (3)
- `update_interval` seconds (10)
- `slow_alert_cooldown_minutes` (30)
- `default_latency_threshold` ms (100)

## Discord Setup
1. Create application → add Bot.
2. Enable Server Members Intent and Message Content Intent.
3. OAuth2 URL generator: scopes `bot`, `applications.commands`; permissions above.
4. Invite bot to your server.

## Project Structure
```
├── main.py
├── bot.py
├── config.py
├── models.py
├── monitor.py
├── requirements.txt
├── LICENSE
└── README.md
```

## Docker (optional)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```
```bash
docker build -t discord-monitor .
docker run -d --env-file .env discord-monitor
```

## License
Creative Commons Attribution-NonCommercial 4.0 International. See `LICENSE`.

## What's New (v2 Revamp)
- Complete refactor to a modular structure (`main.py`, `bot.py`, `config.py`, `monitor.py`, `models.py`).
- Live status dashboard with categories, latency display, and downtime tracking.
- Incident embeds auto-create on outages, update on recovery, and include a Clear button.
- Robust alerting: skips bots and users with DMs disabled; clean `@everyone` notification.
- Config-driven setup: `.env` for secrets; `config.py` for services and thresholds.
- Minimal CI workflow to validate imports on push.
