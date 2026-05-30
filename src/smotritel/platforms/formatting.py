from __future__ import annotations

import html

from smotritel.core.dto import ContainerStatus, ProviderResult, SystemStatus


def format_system_status_html(title: str, status: SystemStatus) -> str:
    return (
        f"<b>{html.escape(title)}</b>\n\n"
        f"<b>Uptime:</b> <code>{html.escape(status.uptime)}</code>\n"
        f"<b>CPU:</b> <code>{status.cpu_percent}%</code>\n"
        f"<b>RAM:</b> <code>{status.ram_used_gb}GB / {status.ram_total_gb}GB ({status.ram_percent}%)</code>\n"
        f"<b>Disk:</b> <code>{status.disk_used_gb}GB / {status.disk_total_gb}GB ({status.disk_percent}%)</code>\n"
        f"<b>Ping:</b> <code>{html.escape(status.ping)}</code>"
    )


def format_system_status_text(title: str, status: SystemStatus) -> str:
    prefix = f"{title}\n\n" if title else ""
    return (
        f"{prefix}"
        f"Uptime: {status.uptime}\n"
        f"CPU: {status.cpu_percent}%\n"
        f"RAM: {status.ram_used_gb}GB / {status.ram_total_gb}GB ({status.ram_percent}%)\n"
        f"Disk: {status.disk_used_gb}GB / {status.disk_total_gb}GB ({status.disk_percent}%)\n"
        f"Ping: {status.ping}"
    )


def format_container_lines(containers: list[ContainerStatus]) -> str:
    return "\n".join(f"{c.name} | {c.status} | {c.uptime}" for c in containers)


def format_provider_result(result: ProviderResult) -> str:
    lines = [result.message]
    if result.details:
        lines.extend(f"{key}: {value}" for key, value in result.details.items())
    return "\n".join(lines)


def html_code_block(text: str, limit: int = 3500) -> str:
    escaped = html.escape(text or "")
    if len(escaped) > limit:
        escaped = escaped[-limit:]
    return f"<code>{escaped}</code>"
