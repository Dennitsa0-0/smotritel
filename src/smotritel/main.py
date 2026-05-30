from __future__ import annotations

import asyncio
import logging
import signal
from contextlib import suppress

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .config import Settings
from .core import DockerProvider, Fail2BanProvider, SystemMonitor
from .i18n import Localization

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)


async def amain() -> None:
    settings = Settings.from_env()
    i18n = Localization(settings.app_lang)
    monitor = SystemMonitor()
    docker_provider = DockerProvider(settings.self_container_name)
    f2b_provider = Fail2BanProvider(settings.f2b_sock_path)
    scheduler = AsyncIOScheduler()
    stop_event = asyncio.Event()
    platforms = []

    if settings.tg_bot_token:
        from .platforms.telegram import TelegramPlatform

        platforms.append(TelegramPlatform(settings, i18n, monitor, docker_provider, f2b_provider))
    else:
        log.info("Telegram token is empty; Telegram platform skipped")

    if settings.discord_bot_token:
        from .platforms.discord import DiscordPlatform

        platforms.append(DiscordPlatform(settings, i18n, monitor, docker_provider, f2b_provider))
    else:
        log.info("Discord token is empty; Discord platform skipped")

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop_event.set)

    async def scheduled_report() -> None:
        await asyncio.gather(
            *(platform.send_scheduled_report() for platform in platforms if hasattr(platform, "send_scheduled_report")),
            return_exceptions=True,
        )

    tasks = [asyncio.create_task(platform.start()) for platform in platforms]
    scheduler_started = False
    try:
        if not tasks:
            log.warning("No platforms enabled. Set TG_BOT_TOKEN or DISCORD_BOT_TOKEN.")
            return
        scheduler.add_job(scheduled_report, "interval", hours=settings.monitor_interval_hours)
        scheduler.start()
        scheduler_started = True
        await stop_event.wait()
    finally:
        if scheduler_started:
            scheduler.shutdown(wait=False)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.gather(*(platform.close() for platform in platforms), return_exceptions=True)
        docker_provider.close()


def run() -> None:
    asyncio.run(amain())
