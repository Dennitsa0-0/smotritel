from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any

from .dto import ContainerStatus, ProviderResult

ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def sanitize_log_text(text: str, max_chars: int = 3500) -> str:
    cleaned = ANSI_RE.sub("", text).replace("\x00", "")
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[-max_chars:]


class DockerProvider:
    def __init__(self, self_container_name: str = "Smotritel", client: Any | None = None) -> None:
        self.self_container_name = self_container_name
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            import docker

            self._client = docker.from_env()
        return self._client

    async def get_containers_status(self) -> list[ContainerStatus]:
        return await asyncio.to_thread(self._get_containers_status_sync)

    async def restart_container(self, container_name: str) -> ProviderResult:
        return await asyncio.to_thread(self._restart_container_sync, container_name)

    async def get_container_logs(self, container_name: str, tail_lines: int = 20, max_chars: int = 3500) -> str:
        return await asyncio.to_thread(self._get_container_logs_sync, container_name, tail_lines, max_chars)

    def close(self) -> None:
        if self._client is not None:
            close = getattr(self._client, "close", None)
            if close:
                close()

    def _get_containers_status_sync(self) -> list[ContainerStatus]:
        containers = self.client.containers.list(all=True)
        return [self._to_status(container) for container in containers]

    def _restart_container_sync(self, container_name: str) -> ProviderResult:
        if container_name == self.self_container_name:
            return ProviderResult(False, "Restart of Smotritel container is blocked.")
        try:
            container = self.client.containers.get(container_name)
            container.restart()
            return ProviderResult(True, f"Container {container_name} restarted.")
        except Exception as exc:
            return ProviderResult(False, "Docker restart failed.", {"error": str(exc)})

    def _get_container_logs_sync(self, container_name: str, tail_lines: int, max_chars: int) -> str:
        container = self.client.containers.get(container_name)
        raw = container.logs(tail=tail_lines)
        text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
        return sanitize_log_text(text, max_chars=max_chars)

    def _to_status(self, container: Any) -> ContainerStatus:
        attrs = getattr(container, "attrs", {}) or {}
        state = attrs.get("State", {}) or {}
        health = (state.get("Health") or {}).get("Status")
        return ContainerStatus(
            name=getattr(container, "name", ""),
            status=getattr(container, "status", state.get("Status", "unknown")),
            uptime=self._uptime_from_started_at(state.get("StartedAt")),
            health=health,
        )

    @staticmethod
    def _uptime_from_started_at(started_at: str | None) -> str:
        if not started_at or started_at.startswith("0001-"):
            return "not running"
        try:
            started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            delta = datetime.now(timezone.utc) - started.astimezone(timezone.utc)
            return str(delta).split(".")[0]
        except Exception:
            return "unknown"
