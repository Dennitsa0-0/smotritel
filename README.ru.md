# Smotritel

Smotritel - легковесный async DevOps-информер для Linux-серверов. Он показывает метрики хоста, состояние Docker-контейнеров, логи, перезапуск контейнеров и разбан Fail2Ban через Telegram и Discord.

Проект специально остается небольшим: серверная логика отделена от Telegram/Discord интерфейсов, чтобы код было легко проверить перед запуском на продакшн-хосте.

## Возможности

- Статус хоста: hostname, uptime, CPU, RAM, диск и ping.
- Список Docker-контейнеров со статусом и uptime.
- Просмотр обрезанных логов контейнера.
- Перезапуск Docker-контейнеров с защитой от перезапуска самого Smotritel.
- Разбан Fail2Ban напрямую через Unix-сокет без установки `fail2ban-client` внутри контейнера.
- Запуск Telegram, Discord или обеих платформ сразу.
- Локализация `en` и `ru`.

## Требования к серверу

- Linux-сервер с Docker Engine и Docker Compose plugin.
- Python на хосте не нужен, если запуск идет через Docker.
- Опционально: установленный и запущенный Fail2Ban.
- Опционально: Telegram bot token.
- Опционально: Discord bot token.

Нужен хотя бы один токен:

- `TG_BOT_TOKEN` для Telegram
- `DISCORD_BOT_TOKEN` для Discord

## Безопасность

Smotritel - админский инструмент. Относитесь к нему как к привилегированному сервису.

Контейнер монтирует:

- `/var/run/docker.sock`
- `/var/run/fail2ban/fail2ban.sock`
- `/hostfs/etc/hostname` через read-only mount `/hostfs`

Доступ на запись к Docker socket фактически дает контроль над хостом. Любой администратор бота сможет перезапускать контейнеры и читать логи. Храните токены приватно, строго задавайте списки admin ID и запускайте бота только для доверенных операторов.

Перезапуск контейнера Smotritel блокируется, чтобы избежать self-restart loop.

## Лицензия

Smotritel распространяется по Smotritel Non-Commercial License 1.0.

Код можно копировать, изменять и распространять для некоммерческого использования. Нельзя продавать код, брать плату за доступ к нему или использовать его как часть платного продукта, платного сервиса, SaaS, клиентской разработки/консалтинга или другой коммерческой активности без письменного разрешения правообладателя.

## Быстрый деплой

Клонируйте репозиторий на сервер:

```bash
git clone git@github.com:Dennitsa0-0/smotritel.git
cd smotritel
```

Создайте конфиг:

```bash
cp .env.example .env
nano .env
```

Запустите:

```bash
docker compose up --build -d
docker compose logs -f
```

## Конфигурация

```env
APP_LANG=ru
MONITOR_INTERVAL_HOURS=1
SMOTRITEL_CONTAINER_NAME=Smotritel

TG_BOT_TOKEN=
TG_ADMIN_IDS=12345678,98765432

DISCORD_BOT_TOKEN=
DISCORD_ADMIN_IDS=112233445566,778899

F2B_SOCK_PATH=/var/run/fail2ban/fail2ban.sock
```

Важно:

- `APP_LANG` поддерживает `en` и `ru`.
- `TG_ADMIN_IDS` и `DISCORD_ADMIN_IDS` задаются через запятую.
- Старые ключи `BOT_TOKEN` и `ADMIN_IDS` намеренно игнорируются. Используйте `TG_BOT_TOKEN` и `TG_ADMIN_IDS`.
- Если токен платформы пустой, платформа пропускается.
- Если оба токена пустые, приложение корректно завершится.

## Проверка сокетов

Перед деплоем проверьте:

```bash
ls -l /var/run/docker.sock
ls -l /var/run/fail2ban/fail2ban.sock
```

Если Fail2Ban не установлен или не запущен, Docker и статус могут работать, но разбан вернет аккуратную ошибку в боте.

## Эксплуатация

Запуск или обновление:

```bash
docker compose up --build -d
```

Логи:

```bash
docker compose logs -f
```

Перезапуск бота:

```bash
docker compose restart smotritel
```

Остановка:

```bash
docker compose down
```

Обновление из Git:

```bash
git pull
docker compose up --build -d
```

## Диагностика

Бот не стартует:

- Проверьте `.env`.
- Должен быть указан `TG_BOT_TOKEN` или `DISCORD_BOT_TOKEN`.
- Посмотрите `docker compose logs -f`.

Telegram не отвечает:

- Проверьте `TG_BOT_TOKEN`.
- Проверьте, что ваш numeric user ID есть в `TG_ADMIN_IDS`.
- Неадмины игнорируются молча.

Docker-кнопки не работают:

- Проверьте `/var/run/docker.sock`.
- Проверьте volume mount в `docker-compose.yml`.
- Проверьте, что Docker Engine запущен.

Fail2Ban-разбан не работает:

- Проверьте, что Fail2Ban запущен на хосте.
- Проверьте `F2B_SOCK_PATH`.
- Проверьте права на `/var/run/fail2ban/fail2ban.sock`.

Имя сервера неверное:

- В Docker Smotritel сначала читает `/hostfs/etc/hostname`.
- Потом fallback: `/etc/hostname`, `socket.gethostname()`, затем `Сервер`.

## Для разработки

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -e .[dev]
.venv\Scripts\python -m pytest
```
