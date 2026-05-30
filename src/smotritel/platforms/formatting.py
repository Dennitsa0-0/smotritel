from __future__ import annotations

import html

from smotritel.core.dto import ContainerStatus, ProviderResult, SystemStatus

CONTAINER_PAGE_SIZE = 10
DISCORD_SELECT_PAGE_SIZE = 25


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


def sorted_containers(containers: list[ContainerStatus]) -> list[ContainerStatus]:
    return sorted(containers, key=lambda c: c.name.casefold())


def page_count(total_items: int, page_size: int) -> int:
    if total_items <= 0:
        return 1
    return (total_items - 1) // page_size + 1


def clamp_page(page: int, total_items: int, page_size: int) -> int:
    return max(0, min(page, page_count(total_items, page_size) - 1))


def container_page(containers: list[ContainerStatus], page: int, page_size: int) -> tuple[list[ContainerStatus], int, int]:
    ordered = sorted_containers(containers)
    current_page = clamp_page(page, len(ordered), page_size)
    start = current_page * page_size
    return ordered[start : start + page_size], current_page, page_count(len(ordered), page_size)


def container_at_page_index(containers: list[ContainerStatus], page: int, index: int, page_size: int) -> ContainerStatus | None:
    ordered = sorted_containers(containers)
    absolute_index = page * page_size + index
    if absolute_index < 0 or absolute_index >= len(ordered):
        return None
    return ordered[absolute_index]


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
