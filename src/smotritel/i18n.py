from __future__ import annotations


MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "app_ready": "Smotritel is online. Server control panel is active.",
        "access_denied": "Access denied.",
        "status_loading": "Collecting server metrics...",
        "server_fallback": "Server",
        "scheduled_report_title": "Scheduled report",
        "docker_loading": "Reading Docker state...",
        "docker_empty": "No containers found.",
        "docker_error": "Docker is unavailable right now.",
        "logs_empty": "No logs returned.",
        "unban_choose": "Choose Fail2Ban unban mode.",
        "unban_all": "Unban all",
        "unban_ips": "Unban IPs",
        "unban_wait_ips": "Send one or more IPv4/IPv6 addresses separated by spaces, commas, or new lines.",
        "unban_no_valid_ips": "No valid IP addresses found.",
        "ok": "OK",
        "error": "Error",
    },
    "ru": {
        "app_ready": "Смотритель на связи. Пульт управления сервером активирован.",
        "access_denied": "Доступ запрещен.",
        "status_loading": "Собираю метрики сервера...",
        "server_fallback": "Сервер",
        "scheduled_report_title": "Плановый отчет",
        "docker_loading": "Читаю состояние Docker...",
        "docker_empty": "Контейнеры не найдены.",
        "docker_error": "Docker сейчас недоступен.",
        "logs_empty": "Логи не вернули данных.",
        "unban_choose": "Выбери режим разбана Fail2Ban.",
        "unban_all": "Разбанить всех",
        "unban_ips": "Разбанить IP",
        "unban_wait_ips": "Отправь один или несколько IPv4/IPv6 адресов через пробел, запятую или новую строку.",
        "unban_no_valid_ips": "Валидные IP-адреса не найдены.",
        "ok": "Готово",
        "error": "Ошибка",
    },
}


class Localization:
    def __init__(self, lang: str = "en") -> None:
        self.lang = lang if lang in MESSAGES else "en"

    def get(self, key: str, **kwargs: object) -> str:
        template = MESSAGES.get(self.lang, MESSAGES["en"]).get(key, MESSAGES["en"].get(key, key))
        return template.format(**kwargs)
