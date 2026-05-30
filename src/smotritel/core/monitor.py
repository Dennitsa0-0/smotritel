from __future__ import annotations

import asyncio
import re
import socket
import subprocess
from datetime import datetime
from pathlib import Path

import psutil

from .dto import SystemStatus


class SystemMonitor:
    def __init__(self, ping_host: str = "8.8.8.8", hostname_files: tuple[str, ...] | None = None) -> None:
        self.ping_host = ping_host
        self.hostname_files = hostname_files or ("/hostfs/etc/hostname", "/etc/hostname")

    async def get_status(self) -> SystemStatus:
        return await asyncio.to_thread(self._collect)

    def _collect(self) -> SystemStatus:
        cpu_usage = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = str(datetime.now() - boot_time).split(".")[0]
        return SystemStatus(
            host_name=self._host_name(),
            cpu_percent=cpu_usage,
            ram_total_gb=round(ram.total / (1024**3), 2),
            ram_used_gb=round(ram.used / (1024**3), 2),
            ram_percent=ram.percent,
            disk_total_gb=round(disk.total / (1024**3), 2),
            disk_used_gb=round(disk.used / (1024**3), 2),
            disk_percent=disk.percent,
            uptime=uptime,
            ping=self._ping(),
        )

    def _host_name(self) -> str:
        for filename in self.hostname_files:
            try:
                value = Path(filename).read_text(encoding="utf-8").strip()
            except Exception:
                continue
            if value:
                return value
        try:
            return socket.gethostname().strip()
        except Exception:
            return ""

    def _ping(self) -> str:
        commands = [
            ["ping", "-c", "1", "-W", "2", self.ping_host],
            ["ping", "-n", "1", "-w", "2000", self.ping_host],
        ]
        for command in commands:
            try:
                output = subprocess.check_output(command, stderr=subprocess.STDOUT, text=True, timeout=3)
            except Exception:
                continue
            match = re.search(r"time[=<]([\d.]+)\s*ms", output)
            if match:
                return f"{match.group(1)} ms"
        return "unavailable"
