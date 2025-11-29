"""
Configuration management for the Discord Service Monitor Bot.
Uses environment variables for sensitive data and provides sensible defaults.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class MonitoringConfig:
    ping_attempts: int = 3
    ping_delay: float = 0.5
    http_timeout: int = 5
    failure_threshold: int = 3
    update_interval: int = 10
    slow_alert_cooldown_minutes: int = 30
    default_latency_threshold: int = 100


@dataclass
class DiscordConfig:
    token: str = field(default_factory=lambda: os.getenv("DISCORD_TOKEN", ""))
    # Channels/role are now set via /setup; default to 0/empty without failing when envs are missing
    channel_id: int = field(default_factory=lambda: int(os.getenv("CHANNEL_ID", "0") or "0"))
    alert_channel_id: int = field(default_factory=lambda: int(os.getenv("ALERT_CHANNEL_ID", "0") or "0"))
    alert_role_name: str = field(default_factory=lambda: os.getenv("ALERT_ROLE_NAME", ""))

    def validate(self) -> None:
        if not self.token:
            raise ValueError("DISCORD_TOKEN environment variable is required")
        # CHANNEL_ID and ALERT_CHANNEL_ID are optional at startup; they can be set via /setup.


@dataclass
class ServiceConfig:
    """
    Define what to monitor.

    Fields:
    - websites: List of website URLs to check (expects HTTP 200).
    - servers: Mapping of a friendly name -> IP/host to ping.
    - latency_thresholds: Optional per-service latency thresholds in ms (key must match a server name).
    - service_categories: Optional grouping for the dashboard embed.

    Quick examples (uncomment and adapt):
        # websites=["https://example.com", "https://status.example.com/health"],
        # servers={"Edge Router": "203.0.113.10", "Game Server": "192.0.2.50"},
        # latency_thresholds={"Game Server": 60},
        # service_categories={"Websites": ["https://example.com"], "Servers": ["Game Server"]}
    """
    websites: List[str] = field(default_factory=list)
    servers: Dict[str, str] = field(default_factory=dict)
    latency_thresholds: Dict[str, int] = field(default_factory=dict)
    service_categories: Dict[str, List[str]] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "ServiceConfig":
        # Start with empty defaults. Add your own in this method or edit at runtime.
        # Nothing user-specific ships by default.
        return cls(
            websites=[],
            servers={},
            latency_thresholds={},
            service_categories={},
        )


class Config:
    def __init__(self):
        self.discord = DiscordConfig()
        self.monitoring = MonitoringConfig()
        self.services = ServiceConfig.from_env()

    def validate(self) -> None:
        self.discord.validate()
        # Services may be empty at first; users add them via slash commands.


def load_config() -> "Config":
    config = Config()
    config.validate()
    return config
