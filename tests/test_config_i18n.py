import pytest

from smotritel.config import Settings, parse_admin_ids
from smotritel.i18n import Localization


def test_parse_admin_ids() -> None:
    assert parse_admin_ids("1, 2,3") == [1, 2, 3]


def test_parse_admin_ids_rejects_invalid() -> None:
    with pytest.raises(ValueError):
        parse_admin_ids("1,nope")


def test_settings_from_env() -> None:
    settings = Settings.from_env(
        {
            "APP_LANG": "ru",
            "MONITOR_INTERVAL_HOURS": "2",
            "TG_BOT_TOKEN": "tg",
            "TG_ADMIN_IDS": "10,20",
            "DISCORD_BOT_TOKEN": "",
            "DISCORD_ADMIN_IDS": "30",
            "F2B_SOCK_PATH": "/tmp/f2b.sock",
        }
    )
    assert settings.app_lang == "ru"
    assert settings.tg_admin_ids == [10, 20]
    assert settings.discord_bot_token is None


def test_i18n_fallback() -> None:
    assert Localization("xx").get("ok") == "OK"
    assert Localization("en").get("missing_key") == "missing_key"
