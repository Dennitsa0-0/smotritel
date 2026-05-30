from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from dotenv import load_dotenv


def parse_admin_ids(raw: str) -> list[int]:
    ids: list[int] = []
    for item in raw.split(","):
        item = item.strip()
        if item:
            ids.append(int(item))
    return ids


def _get_int(env: Mapping[str, str], key: str, default: int) -> int:
    raw = env.get(key, "").strip()
    if not raw:
        return default
    value = int(raw)
    if value <= 0:
        raise ValueError(f"{key} must be positive")
    return value


@dataclass(frozen=True)
class Settings:
    app_lang: str
    monitor_interval_hours: int
    tg_bot_token: str | None
    tg_admin_ids: list[int]
    discord_bot_token: str | None
    discord_admin_ids: list[int]
    f2b_sock_path: str
    self_container_name: str

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        load_dotenv()
        source = env if env is not None else os.environ
        lang = source.get("APP_LANG", "en").strip().lower() or "en"
        if lang not in {"en", "ru"}:
            lang = "en"
        return cls(
            app_lang=lang,
            monitor_interval_hours=_get_int(source, "MONITOR_INTERVAL_HOURS", 1),
            tg_bot_token=source.get("TG_BOT_TOKEN") or None,
            tg_admin_ids=parse_admin_ids(source.get("TG_ADMIN_IDS", "")),
            discord_bot_token=source.get("DISCORD_BOT_TOKEN") or None,
            discord_admin_ids=parse_admin_ids(source.get("DISCORD_ADMIN_IDS", "")),
            f2b_sock_path=source.get("F2B_SOCK_PATH", "/var/run/fail2ban/fail2ban.sock"),
            self_container_name=source.get("SMOTRITEL_CONTAINER_NAME", "Smotritel"),
        )
