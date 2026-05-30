from __future__ import annotations

import logging
import time
from collections import defaultdict

import discord
from discord import app_commands

from smotritel.config import Settings
from smotritel.core import ContainerStatus, DockerProvider, Fail2BanProvider, SystemMonitor, parse_ip_input
from smotritel.i18n import Localization
from smotritel.platforms.formatting import (
    DISCORD_SELECT_PAGE_SIZE,
    container_at_page_index,
    container_page,
    format_container_lines,
    format_provider_result,
    format_system_status_text,
    sorted_containers,
)

log = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self, cooldown_seconds: float = 2.0) -> None:
        self.cooldown_seconds = cooldown_seconds
        self._hits: dict[tuple[int, str], float] = defaultdict(float)

    def allow(self, user_id: int, action: str) -> bool:
        key = (user_id, action)
        now = time.monotonic()
        if now - self._hits[key] < self.cooldown_seconds:
            return False
        self._hits[key] = now
        return True


class DiscordPlatform:
    def __init__(
        self,
        settings: Settings,
        i18n: Localization,
        monitor: SystemMonitor,
        docker_provider: DockerProvider,
        f2b_provider: Fail2BanProvider,
    ) -> None:
        intents = discord.Intents.default()
        self.client = discord.Client(intents=intents)
        self.tree = app_commands.CommandTree(self.client)
        self.settings = settings
        self.i18n = i18n
        self.monitor = monitor
        self.docker = docker_provider
        self.f2b = f2b_provider
        self.rate_limiter = RateLimiter()
        self._register()

    async def start(self) -> None:
        log.info("Starting Discord platform")
        await self.client.start(self.settings.discord_bot_token or "")

    async def close(self) -> None:
        await self.client.close()

    async def send_scheduled_report(self) -> None:
        data = await self.monitor.get_status()
        embed = discord.Embed(
            title=f"{self.i18n.get('scheduled_report_title')}: {self._status_title(data.host_name)}",
            description=format_system_status_text("", data),
            color=0xFF0000 if data.cpu_percent > 90 else 0x00FF00,
        )
        for admin_id in self.settings.discord_admin_ids:
            try:
                user = await self.client.fetch_user(admin_id)
                await user.send(embed=embed)
            except Exception:
                log.exception("Failed to send Discord scheduled report to %s", admin_id)

    def _is_admin(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id in self.settings.discord_admin_ids

    def _status_title(self, host_name: str) -> str:
        return host_name.strip() or self.i18n.get("server_fallback")

    async def _get_sorted_containers(self) -> list[ContainerStatus]:
        return sorted_containers(await self.docker.get_containers_status())

    def _register(self) -> None:
        @self.client.event
        async def on_ready() -> None:
            await self.tree.sync()
            log.info("Discord platform is ready as %s", self.client.user)

        @self.tree.command(name="status", description="Show server status")
        async def status(interaction: discord.Interaction) -> None:
            if not self._is_admin(interaction):
                await interaction.response.send_message(self.i18n.get("access_denied"), ephemeral=True)
                return
            if not self.rate_limiter.allow(interaction.user.id, "status"):
                await interaction.response.send_message("Slow down a little.", ephemeral=True)
                return
            data = await self.monitor.get_status()
            color = 0xFF0000 if data.cpu_percent > 90 else 0x00FF00
            embed = discord.Embed(
                title=self._status_title(data.host_name),
                description=format_system_status_text("", data),
                color=color,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        @self.tree.command(name="docker", description="Show Docker containers")
        async def docker_status(interaction: discord.Interaction) -> None:
            if not self._is_admin(interaction):
                await interaction.response.send_message(self.i18n.get("access_denied"), ephemeral=True)
                return
            if not self.rate_limiter.allow(interaction.user.id, "docker"):
                await interaction.response.send_message("Slow down a little.", ephemeral=True)
                return
            try:
                containers = await self._get_sorted_containers()
            except Exception as exc:
                await interaction.response.send_message(f"{self.i18n.get('docker_error')}: {exc}", ephemeral=True)
                return
            if not containers:
                await interaction.response.send_message(self.i18n.get("docker_empty"), ephemeral=True)
                return
            color = 0x00FF00 if all(c.is_healthy for c in containers) else 0xFF0000
            embed = discord.Embed(title="Docker", description=format_container_lines(containers), color=color)
            await interaction.response.send_message(embed=embed, view=DockerView(self, containers), ephemeral=True)

        @self.tree.command(name="unban_all", description="Unban all Fail2Ban IPs")
        async def unban_all_command(interaction: discord.Interaction) -> None:
            if not self._is_admin(interaction):
                await interaction.response.send_message(self.i18n.get("access_denied"), ephemeral=True)
                return
            if not self.rate_limiter.allow(interaction.user.id, "f2b_unban_all_command"):
                await interaction.response.send_message("Slow down a little.", ephemeral=True)
                return
            result = await self.f2b.unban_all()
            await interaction.response.send_message(format_provider_result(result), ephemeral=True)

        @self.tree.command(name="unban_ips", description="Unban specific Fail2Ban IPs")
        async def unban_ips_command(interaction: discord.Interaction, ips: str) -> None:
            if not self._is_admin(interaction):
                await interaction.response.send_message(self.i18n.get("access_denied"), ephemeral=True)
                return
            if not self.rate_limiter.allow(interaction.user.id, "f2b_unban_ips_command"):
                await interaction.response.send_message("Slow down a little.", ephemeral=True)
                return
            parsed = parse_ip_input(ips)
            if not parsed:
                await interaction.response.send_message(self.i18n.get("unban_no_valid_ips"), ephemeral=True)
                return
            result = await self.f2b.unban_ips(parsed)
            await interaction.response.send_message(format_provider_result(result), ephemeral=True)


class DockerView(discord.ui.View):
    def __init__(self, platform: DiscordPlatform, containers: list[ContainerStatus], page: int = 0) -> None:
        super().__init__(timeout=120)
        self.platform = platform
        page_items, current_page, total_pages = container_page(containers, page, DISCORD_SELECT_PAGE_SIZE)
        self.add_item(_DockerSelect(platform, page_items, current_page))
        if total_pages > 1:
            self.add_item(_DockerPageButton(platform, "<", max(0, current_page - 1)))
            self.add_item(_DockerPageButton(platform, ">", min(total_pages - 1, current_page + 1)))
        self.add_item(_F2BUnbanAllButton(platform))


class _DockerSelect(discord.ui.Select):
    def __init__(self, platform: DiscordPlatform, containers: list[ContainerStatus], page: int) -> None:
        options = [
            discord.SelectOption(
                label=container.name[:100],
                description=f"{container.status} | {container.uptime}"[:100],
                value=str(index),
            )
            for index, container in enumerate(containers)
        ]
        super().__init__(placeholder="Choose a container", min_values=1, max_values=1, options=options)
        self.platform = platform
        self.page = page

    async def callback(self, interaction: discord.Interaction) -> None:
        if not self.platform._is_admin(interaction):
            await interaction.response.send_message(self.platform.i18n.get("access_denied"), ephemeral=True)
            return
        if not self.platform.rate_limiter.allow(interaction.user.id, "docker_select"):
            await interaction.response.send_message("Slow down a little.", ephemeral=True)
            return
        try:
            containers = await self.platform._get_sorted_containers()
        except Exception as exc:
            await interaction.response.send_message(f"{self.platform.i18n.get('docker_error')}: {exc}", ephemeral=True)
            return
        container = container_at_page_index(
            containers,
            self.page,
            int(self.values[0]),
            DISCORD_SELECT_PAGE_SIZE,
        )
        if container is None:
            await interaction.response.send_message(self.platform.i18n.get("docker_empty"), ephemeral=True)
            return
        embed = discord.Embed(
            title=container.name,
            description=f"{container.status} | {container.uptime}",
            color=0x00FF00 if container.is_healthy else 0xFF0000,
        )
        await interaction.response.edit_message(embed=embed, view=DockerContainerView(self.platform, self.page, int(self.values[0])))


class _DockerPageButton(discord.ui.Button):
    def __init__(self, platform: DiscordPlatform, label: str, page: int) -> None:
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.platform = platform
        self.page = page

    async def callback(self, interaction: discord.Interaction) -> None:
        if not self.platform._is_admin(interaction):
            await interaction.response.send_message(self.platform.i18n.get("access_denied"), ephemeral=True)
            return
        try:
            containers = await self.platform._get_sorted_containers()
        except Exception as exc:
            await interaction.response.send_message(f"{self.platform.i18n.get('docker_error')}: {exc}", ephemeral=True)
            return
        color = 0x00FF00 if all(c.is_healthy for c in containers) else 0xFF0000
        embed = discord.Embed(title="Docker", description=format_container_lines(containers), color=color)
        await interaction.response.edit_message(embed=embed, view=DockerView(self.platform, containers, self.page))


class DockerContainerView(discord.ui.View):
    def __init__(self, platform: DiscordPlatform, page: int, index: int) -> None:
        super().__init__(timeout=120)
        self.add_item(_DockerLogsButton(platform, page, index))
        self.add_item(_DockerRestartButton(platform, page, index))
        self.add_item(_DockerBackButton(platform, page))


class _DockerLogsButton(discord.ui.Button):
    def __init__(self, platform: DiscordPlatform, page: int, index: int) -> None:
        super().__init__(label="Logs", style=discord.ButtonStyle.secondary)
        self.platform = platform
        self.page = page
        self.index = index

    async def callback(self, interaction: discord.Interaction) -> None:
        if not self.platform._is_admin(interaction):
            await interaction.response.send_message(self.platform.i18n.get("access_denied"), ephemeral=True)
            return
        if not self.platform.rate_limiter.allow(interaction.user.id, f"docker_logs:{self.page}:{self.index}"):
            await interaction.response.send_message("Slow down a little.", ephemeral=True)
            return
        try:
            containers = await self.platform._get_sorted_containers()
            container = container_at_page_index(containers, self.page, self.index, DISCORD_SELECT_PAGE_SIZE)
            if container is None:
                await interaction.response.send_message(self.platform.i18n.get("docker_empty"), ephemeral=True)
                return
            logs = await self.platform.docker.get_container_logs(container.name)
        except Exception as exc:
            await interaction.response.send_message(f"{self.platform.i18n.get('docker_error')}: {exc}", ephemeral=True)
            return
        await interaction.response.send_message(f"```text\n{logs[-1800:]}\n```", ephemeral=True)


class _DockerRestartButton(discord.ui.Button):
    def __init__(self, platform: DiscordPlatform, page: int, index: int) -> None:
        super().__init__(label="Restart", style=discord.ButtonStyle.danger)
        self.platform = platform
        self.page = page
        self.index = index

    async def callback(self, interaction: discord.Interaction) -> None:
        if not self.platform._is_admin(interaction):
            await interaction.response.send_message(self.platform.i18n.get("access_denied"), ephemeral=True)
            return
        if not self.platform.rate_limiter.allow(interaction.user.id, f"docker_restart:{self.page}:{self.index}"):
            await interaction.response.send_message("Slow down a little.", ephemeral=True)
            return
        try:
            containers = await self.platform._get_sorted_containers()
        except Exception as exc:
            await interaction.response.send_message(f"{self.platform.i18n.get('docker_error')}: {exc}", ephemeral=True)
            return
        container = container_at_page_index(containers, self.page, self.index, DISCORD_SELECT_PAGE_SIZE)
        if container is None:
            await interaction.response.send_message(self.platform.i18n.get("docker_empty"), ephemeral=True)
            return
        result = await self.platform.docker.restart_container(container.name)
        await interaction.response.send_message(format_provider_result(result), ephemeral=True)


class _DockerBackButton(discord.ui.Button):
    def __init__(self, platform: DiscordPlatform, page: int) -> None:
        super().__init__(label="Back", style=discord.ButtonStyle.secondary)
        self.platform = platform
        self.page = page

    async def callback(self, interaction: discord.Interaction) -> None:
        if not self.platform._is_admin(interaction):
            await interaction.response.send_message(self.platform.i18n.get("access_denied"), ephemeral=True)
            return
        try:
            containers = await self.platform._get_sorted_containers()
        except Exception as exc:
            await interaction.response.send_message(f"{self.platform.i18n.get('docker_error')}: {exc}", ephemeral=True)
            return
        color = 0x00FF00 if all(c.is_healthy for c in containers) else 0xFF0000
        embed = discord.Embed(title="Docker", description=format_container_lines(containers), color=color)
        await interaction.response.edit_message(embed=embed, view=DockerView(self.platform, containers, self.page))


class _F2BUnbanAllButton(discord.ui.Button):
    def __init__(self, platform: DiscordPlatform) -> None:
        super().__init__(label="Unban all F2B", style=discord.ButtonStyle.danger)
        self.platform = platform

    async def callback(self, interaction: discord.Interaction) -> None:
        if not self.platform._is_admin(interaction):
            await interaction.response.send_message(self.platform.i18n.get("access_denied"), ephemeral=True)
            return
        if not self.platform.rate_limiter.allow(interaction.user.id, "f2b_unban_all"):
            await interaction.response.send_message("Slow down a little.", ephemeral=True)
            return
        result = await self.platform.f2b.unban_all()
        await interaction.response.send_message(format_provider_result(result), ephemeral=True)
