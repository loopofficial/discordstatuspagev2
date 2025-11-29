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
    channel_id: int = field(default_factory=lambda: int(os.getenv("CHANNEL_ID", "0")))
    alert_channel_id: int = field(default_factory=lambda: int(os.getenv("ALERT_CHANNEL_ID", "0")))
    alert_role_name: str = field(default_factory=lambda: os.getenv("ALERT_ROLE_NAME", ""))

    def validate(self) -> None:
        if not self.token:
            raise ValueError("DISCORD_TOKEN environment variable is required")
        if not self.channel_id:
            raise ValueError("CHANNEL_ID environment variable is required")
        if not self.alert_channel_id:
            raise ValueError("ALERT_CHANNEL_ID environment variable is required")


@dataclass
class ServiceConfig:
    websites: List[str] = field(default_factory=list)
    servers: Dict[str, str] = field(default_factory=dict)
    latency_thresholds: Dict[str, int] = field(default_factory=dict)
    service_categories: Dict[str, List[str]] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "ServiceConfig":
        return cls(
            websites=[],
            servers={},
            latency_thresholds={},
            service_categories={}
        )


class Config:
    def __init__(self):
        self.discord = DiscordConfig()
        self.monitoring = MonitoringConfig()
        self.services = ServiceConfig.from_env()

    def validate(self) -> None:
        self.discord.validate()
        if not self.services.websites and not self.services.servers:
            raise ValueError("At least one website or server must be configured for monitoring")


def load_config() -> "Config":
    config = Config()
    config.validate()
    return config
