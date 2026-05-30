from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SystemStatus:
    host_name: str
    cpu_percent: float
    ram_total_gb: float
    ram_used_gb: float
    ram_percent: float
    disk_total_gb: float
    disk_used_gb: float
    disk_percent: float
    uptime: str
    ping: str


@dataclass(frozen=True)
class ContainerStatus:
    name: str
    status: str
    uptime: str
    health: str | None = None

    @property
    def is_healthy(self) -> bool:
        status_ok = self.status.lower() in {"running", "created"}
        health_ok = self.health is None or self.health.lower() in {"healthy", "none"}
        return status_ok and health_ok


@dataclass(frozen=True)
class ProviderResult:
    ok: bool
    message: str
    details: dict[str, str] = field(default_factory=dict)
