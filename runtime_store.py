import json
import os
import asyncio
from typing import Dict, Any, List

_DEFAULT_DATA = {
    "websites": [],
    "servers": {},  # name -> ip/host
    "latency_thresholds": {},  # service name -> ms
    "status_channel_id": 0,
    "alert_channel_id": 0,
    "alert_role_name": ""
}

class RuntimeStore:
    def __init__(self, path: str = "data/runtime_config.json"):
        self.path = path
        self._lock = asyncio.Lock()
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if not os.path.exists(self.path):
            self._write(_DEFAULT_DATA)
        self._data = self._read()

    def _read(self) -> Dict[str, Any]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return _DEFAULT_DATA.copy()

    def _write(self, data: Dict[str, Any]) -> None:
        tmp_path = self.path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, self.path)

    async def save(self) -> None:
        async with self._lock:
            self._write(self._data)

    async def set_channel_ids(self, status_channel_id: int, alert_channel_id: int) -> None:
        async with self._lock:
            self._data["status_channel_id"] = status_channel_id
            self._data["alert_channel_id"] = alert_channel_id
            self._write(self._data)

    async def set_role_name(self, role_name: str) -> None:
        async with self._lock:
            self._data["alert_role_name"] = role_name
            self._write(self._data)

    async def add_website(self, url: str) -> bool:
        async with self._lock:
            if url in self._data["websites"]:
                return False
            self._data["websites"].append(url)
            self._write(self._data)
            return True

    async def remove_website(self, url: str) -> bool:
        async with self._lock:
            if url not in self._data["websites"]:
                return False
            self._data["websites"].remove(url)
            self._write(self._data)
            return True

    async def add_server(self, name: str, host: str, latency_threshold: int | None = None) -> bool:
        async with self._lock:
            if name in self._data["servers"]:
                return False
            self._data["servers"][name] = host
            if latency_threshold is not None:
                self._data["latency_thresholds"][name] = latency_threshold
            self._write(self._data)
            return True

    async def remove_server(self, name: str) -> bool:
        async with self._lock:
            if name not in self._data["servers"]:
                return False
            self._data["servers"].pop(name)
            self._data["latency_thresholds"].pop(name, None)
            self._write(self._data)
            return True

    async def set_latency(self, name: str, threshold: int) -> bool:
        async with self._lock:
            if name not in self._data["servers"] and name not in self._data["websites"]:
                return False
            self._data["latency_thresholds"][name] = threshold
            self._write(self._data)
            return True

    def snapshot(self) -> Dict[str, Any]:
        return self._data.copy()

    def websites(self) -> List[str]:
        return list(self._data["websites"])

    def servers(self) -> Dict[str, str]:
        return dict(self._data["servers"])

    def latency_thresholds(self) -> Dict[str, int]:
        return dict(self._data["latency_thresholds"])

    def status_channel_id(self) -> int:
        return int(self._data.get("status_channel_id", 0))

    def alert_channel_id(self) -> int:
        return int(self._data.get("alert_channel_id", 0))

    def alert_role_name(self) -> str:
        return self._data.get("alert_role_name", "")
