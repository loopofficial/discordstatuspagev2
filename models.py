from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional
from enum import Enum

class ServiceStatus(Enum):
    UP = "Up"
    DOWN = "Down"
    DEGRADED = "Degraded"

@dataclass
class ServiceState:
    status: ServiceStatus = ServiceStatus.UP
    down_since: Optional[datetime] = None
    latency: Optional[float] = None
    last_slow_alert: Optional[datetime] = None
    incident_message_id: Optional[int] = None
    failure_count: int = 0

    def mark_up(self, latency: Optional[float] = None) -> None:
        self.status = ServiceStatus.UP
        self.down_since = None
        self.latency = latency
        self.failure_count = 0

    def mark_down(self) -> None:
        self.status = ServiceStatus.DOWN
        self.down_since = datetime.now()

    def increment_failure(self) -> None:
        self.failure_count += 1

    def reset_failure_count(self) -> None:
        self.failure_count = 0

    def get_downtime(self) -> Optional[str]:
        if self.down_since:
            duration = datetime.now() - self.down_since
            return str(duration).split('.')[0]
        return None

class ServiceStateManager:
    def __init__(self):
        self._states: Dict[str, ServiceState] = {}

    def initialize(self, service_names: list) -> None:
        for name in service_names:
            if name not in self._states:
                self._states[name] = ServiceState()

    def get(self, service_name: str) -> ServiceState:
        if service_name not in self._states:
            self._states[service_name] = ServiceState()
        return self._states[service_name]

    def get_all(self) -> Dict[str, ServiceState]:
        return self._states.copy()

    def get_down_services(self) -> Dict[str, ServiceState]:
        return {name: state for name, state in self._states.items() if state.status == ServiceStatus.DOWN}

    def __iter__(self):
        return iter(self._states.items())
