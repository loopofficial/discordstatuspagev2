# Discord Service Monitor Bot

Monitor websites and servers from Discord with a live status dashboard, incident reporting, and alerts.

## Features
- Live dashboard: One embed updated in-place with service status, latency, and downtime.
- Incidents: Auto-created when services go down; shows downtime on recovery; clear via button.
- Alerts: Clean `@everyone` ping and DMs to a specific role (skips bots and users with DMs off).
- Command: `!status` returns the current dashboard embed on demand.
- Config-driven: `.env` for secrets, `config.py` for services and thresholds.

## Requirements
- Python 3.8+
- Discord bot permissions: Send Messages, Embed Links, Manage Messages, Read Message History
- Enable "Server Members Intent" in Developer Portal

## Setup (Windows PowerShell)
```powershell
git clone https://github.com/loopofficial/discordstatuspage.git
cd discordstatuspage

python -m venv venv
./venv/Scripts/Activate.ps1
pip install -r requirements.txt

Copy-Item .env.example .env
# Edit .env: DISCORD_TOKEN, CHANNEL_ID, ALERT_CHANNEL_ID, ALERT_ROLE_NAME

# Configure services in config.py (ServiceConfig.from_env)
python main.py
```

## Configure Services
Edit `config.py` → `ServiceConfig.from_env()` with your targets:
```python
return cls(
    websites=["https://your-website.com", "https://api.your-service.com/health"],
    servers={"Game Server": "192.168.1.100"},
    latency_thresholds={"Game Server": 50},
    service_categories={"Websites": ["https://your-website.com"], "Servers": ["Game Server"]}
)
```

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
2. Enable Server Members Intent.
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
├── .env.example
├── .gitignore
└── .github/workflows/ci.yml
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
