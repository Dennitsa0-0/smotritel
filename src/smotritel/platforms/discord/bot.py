from __future__ import annotations

import logging
import time
from collections import defaultdict

import discord
from discord import app_commands

from smotritel.config import Settings
from smotritel.core import ContainerStatus, DockerProvider, Fail2BanProvider, SystemMonitor, parse_ip_input
from smotritel.i18n import Localization
from smotritel.platforms.formatting import format_container_lines, format_provider_result, format_system_status_text

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
                containers = await self.docker.get_containers_status()
            except Exception as exc:
                await interaction.response.send_message(f"{self.i18n.get('docker_error')}: {exc}", ephemeral=True)
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
    def __init__(self, platform: DiscordPlatform, containers: list[ContainerStatus]) -> None:
        super().__init__(timeout=120)
        self.platform = platform
        for container in containers[:5]:
            self.add_item(_DockerLogsButton(platform, container.name))
            self.add_item(_DockerRestartButton(platform, container.name))
        self.add_item(_F2BUnbanAllButton(platform))


class _DockerLogsButton(discord.ui.Button):
    def __init__(self, platform: DiscordPlatform, container_name: str) -> None:
        super().__init__(label=f"Logs: {container_name}", style=discord.ButtonStyle.secondary)
        self.platform = platform
        self.container_name = container_name

    async def callback(self, interaction: discord.Interaction) -> None:
        if not self.platform._is_admin(interaction):
            await interaction.response.send_message(self.platform.i18n.get("access_denied"), ephemeral=True)
            return
        if not self.platform.rate_limiter.allow(interaction.user.id, f"docker_logs:{self.container_name}"):
            await interaction.response.send_message("Slow down a little.", ephemeral=True)
            return
        try:
            logs = await self.platform.docker.get_container_logs(self.container_name)
        except Exception as exc:
            await interaction.response.send_message(f"{self.platform.i18n.get('docker_error')}: {exc}", ephemeral=True)
            return
        await interaction.response.send_message(f"```text\n{logs[-1800:]}\n```", ephemeral=True)


class _DockerRestartButton(discord.ui.Button):
    def __init__(self, platform: DiscordPlatform, container_name: str) -> None:
        super().__init__(label=f"Restart: {container_name}", style=discord.ButtonStyle.danger)
        self.platform = platform
        self.container_name = container_name

    async def callback(self, interaction: discord.Interaction) -> None:
        if not self.platform._is_admin(interaction):
            await interaction.response.send_message(self.platform.i18n.get("access_denied"), ephemeral=True)
            return
        if not self.platform.rate_limiter.allow(interaction.user.id, f"docker_restart:{self.container_name}"):
            await interaction.response.send_message("Slow down a little.", ephemeral=True)
            return
        result = await self.platform.docker.restart_container(self.container_name)
        await interaction.response.send_message(format_provider_result(result), ephemeral=True)


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
