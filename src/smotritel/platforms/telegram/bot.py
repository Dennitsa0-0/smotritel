from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

from smotritel.config import Settings
from smotritel.core import DockerProvider, Fail2BanProvider, SystemMonitor, parse_ip_input
from smotritel.i18n import Localization
from smotritel.platforms.formatting import (
    format_container_lines,
    format_provider_result,
    format_system_status_html,
    html_code_block,
)

log = logging.getLogger(__name__)

STATUS_BTN = "📊 Status"
DOCKER_BTN = "📦 Docker"
UNBAN_BTN = "🔓 Unban F2B"
LOGS_BTN = "📋 Logs"


class UnbanStates(StatesGroup):
    waiting_for_ips = State()


class TelegramPlatform:
    def __init__(
        self,
        settings: Settings,
        i18n: Localization,
        monitor: SystemMonitor,
        docker_provider: DockerProvider,
        f2b_provider: Fail2BanProvider,
    ) -> None:
        self.settings = settings
        self.i18n = i18n
        self.monitor = monitor
        self.docker = docker_provider
        self.f2b = f2b_provider
        self.bot = Bot(token=settings.tg_bot_token or "")
        self.dp = Dispatcher(storage=MemoryStorage())
        self.router = Router()
        self.dp.include_router(self.router)
        self._register_handlers()

    async def start(self) -> None:
        log.info("Starting Telegram platform")
        await self.bot.delete_webhook(drop_pending_updates=True)
        await self.dp.start_polling(self.bot)

    async def close(self) -> None:
        await self.bot.session.close()

    async def send_scheduled_report(self) -> None:
        status_data = await self.monitor.get_status()
        title = f"{self.i18n.get('scheduled_report_title')}: {self._status_title(status_data.host_name)}"
        text = format_system_status_html(title, status_data)
        for admin_id in self.settings.tg_admin_ids:
            try:
                await self.bot.send_message(admin_id, text, parse_mode="HTML")
            except Exception:
                log.exception("Failed to send Telegram scheduled report to %s", admin_id)

    def _status_title(self, host_name: str) -> str:
        return host_name.strip() or self.i18n.get("server_fallback")

    def _is_admin(self, message_or_query: Message | CallbackQuery) -> bool:
        user = message_or_query.from_user
        return bool(user and user.id in self.settings.tg_admin_ids)

    def _main_keyboard(self) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=STATUS_BTN), KeyboardButton(text=DOCKER_BTN)],
                [KeyboardButton(text=UNBAN_BTN), KeyboardButton(text=LOGS_BTN)],
            ],
            resize_keyboard=True,
        )

    def _register_handlers(self) -> None:
        @self.router.message(Command("start"))
        async def cmd_start(message: Message) -> None:
            if not self._is_admin(message):
                return
            await message.answer(self.i18n.get("app_ready"), reply_markup=self._main_keyboard())

        @self.router.message(F.text == STATUS_BTN)
        async def status(message: Message) -> None:
            if not self._is_admin(message):
                return
            msg = await message.answer(self.i18n.get("status_loading"))
            status_data = await self.monitor.get_status()
            await msg.edit_text(
                format_system_status_html(self._status_title(status_data.host_name), status_data),
                parse_mode="HTML",
            )

        @self.router.message(F.text.in_({DOCKER_BTN, LOGS_BTN}))
        async def docker_menu(message: Message) -> None:
            if not self._is_admin(message):
                return
            msg = await message.answer(self.i18n.get("docker_loading"))
            try:
                containers = await self.docker.get_containers_status()
            except Exception as exc:
                log.exception("Docker status failed")
                await msg.edit_text(f"{self.i18n.get('docker_error')}: {exc}")
                return
            if not containers:
                await msg.edit_text(self.i18n.get("docker_empty"))
                return
            buttons = []
            for container in containers:
                buttons.append(
                    [
                        InlineKeyboardButton(text=f"Logs: {container.name}", callback_data=f"docker:logs:{container.name}"),
                        InlineKeyboardButton(text=f"Restart: {container.name}", callback_data=f"docker:restart:{container.name}"),
                    ]
                )
            await msg.edit_text(format_container_lines(containers), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

        @self.router.callback_query(F.data.startswith("docker:logs:"))
        async def docker_logs(query: CallbackQuery) -> None:
            if not self._is_admin(query):
                return
            name = query.data.split(":", 2)[2]
            try:
                logs = await self.docker.get_container_logs(name)
                await query.message.answer(html_code_block(logs or self.i18n.get("logs_empty")), parse_mode="HTML")
            except Exception as exc:
                log.exception("Docker logs failed")
                await query.message.answer(f"{self.i18n.get('docker_error')}: {exc}")
            await query.answer()

        @self.router.callback_query(F.data.startswith("docker:restart:"))
        async def docker_restart(query: CallbackQuery) -> None:
            if not self._is_admin(query):
                return
            name = query.data.split(":", 2)[2]
            result = await self.docker.restart_container(name)
            await query.message.answer(format_provider_result(result))
            await query.answer()

        @self.router.message(F.text == UNBAN_BTN)
        async def unban_menu(message: Message) -> None:
            if not self._is_admin(message):
                return
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=self.i18n.get("unban_all"), callback_data="f2b:unban:all")],
                    [InlineKeyboardButton(text=self.i18n.get("unban_ips"), callback_data="f2b:unban:ips")],
                ]
            )
            await message.answer(self.i18n.get("unban_choose"), reply_markup=keyboard)

        @self.router.callback_query(F.data == "f2b:unban:all")
        async def unban_all(query: CallbackQuery) -> None:
            if not self._is_admin(query):
                return
            result = await self.f2b.unban_all()
            await query.message.answer(format_provider_result(result))
            await query.answer()

        @self.router.callback_query(F.data == "f2b:unban:ips")
        async def unban_ips_start(query: CallbackQuery, state: FSMContext) -> None:
            if not self._is_admin(query):
                return
            await state.set_state(UnbanStates.waiting_for_ips)
            await query.message.answer(self.i18n.get("unban_wait_ips"))
            await query.answer()

        @self.router.message(UnbanStates.waiting_for_ips)
        async def unban_ips_finish(message: Message, state: FSMContext) -> None:
            if not self._is_admin(message):
                return
            ips = parse_ip_input(message.text or "")
            if not ips:
                await message.answer(self.i18n.get("unban_no_valid_ips"))
                return
            result = await self.f2b.unban_ips(ips)
            await state.clear()
            await message.answer(format_provider_result(result))
