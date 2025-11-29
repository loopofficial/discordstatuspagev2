import asyncio
import platform
from typing import Optional, List
from dataclasses import dataclass
import aiohttp

@dataclass
class CheckResult:
    service_name: str
    is_up: bool
    latency: Optional[float] = None
    error: Optional[str] = None

class ServiceMonitor:
    def __init__(self, ping_attempts: int = 3, ping_delay: float = 0.5, http_timeout: int = 5):
        self.ping_attempts = ping_attempts
        self.ping_delay = ping_delay
        self.http_timeout = http_timeout

    async def check_website(self, url: str) -> CheckResult:
        for attempt in range(self.ping_attempts):
            try:
                timeout = aiohttp.ClientTimeout(total=self.http_timeout)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            return CheckResult(service_name=url, is_up=True)
            except aiohttp.ClientError as e:
                if attempt == self.ping_attempts - 1:
                    return CheckResult(service_name=url, is_up=False, error=str(e))
            except asyncio.TimeoutError:
                if attempt == self.ping_attempts - 1:
                    return CheckResult(service_name=url, is_up=False, error="Connection timeout")
            if attempt < self.ping_attempts - 1:
                await asyncio.sleep(self.ping_delay)
        return CheckResult(service_name=url, is_up=False, error="All attempts failed")

    async def check_server_latency(self, service_name: str, ip: str) -> CheckResult:
        latencies: List[float] = []
        for attempt in range(self.ping_attempts):
            latency = await self._ping(ip)
            if latency is not None:
                latencies.append(latency)
            if attempt < self.ping_attempts - 1:
                await asyncio.sleep(self.ping_delay)
        if latencies:
            avg_latency = round(sum(latencies) / len(latencies), 2)
            return CheckResult(service_name=service_name, is_up=True, latency=avg_latency)
        return CheckResult(service_name=service_name, is_up=False, error="Ping failed")

    async def _ping(self, ip: str) -> Optional[float]:
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        command = ['ping', param, '1', ip]
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            if process.returncode == 0:
                return self._parse_ping_output(stdout.decode())
        except Exception:
            pass
        return None

    @staticmethod
    def _parse_ping_output(output: str) -> Optional[float]:
        try:
            if 'time=' in output:
                time_part = output.split('time=')[-1]
                latency_str = time_part.split('ms')[0].strip().replace('<', '')
                return float(latency_str)
        except (IndexError, ValueError):
            pass
        return None

    async def check_all(self, websites: List[str], servers: dict) -> List[CheckResult]:
        tasks = []
        for url in websites:
            tasks.append(self.check_website(url))
        for name, ip in servers.items():
            tasks.append(self.check_server_latency(name, ip))
        return await asyncio.gather(*tasks)
