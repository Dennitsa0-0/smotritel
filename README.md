# Smotritel

[Русский](#русский) | [English](#english)

Repository: [Dennitsa0-0/smotritel](https://github.com/Dennitsa0-0/smotritel.git)  
Companion project: [Dennitsa0-0/Radar_Bot](https://github.com/Dennitsa0-0/Radar_Bot.git)

## Русский

Smotritel - легковесный async DevOps-информер для Linux-серверов. Он показывает состояние хоста, Docker-контейнеры, логи, перезапуск контейнеров и разбан Fail2Ban через Telegram и Discord.

Проект хорошо работает сам по себе, но идеально раскрывается в связке с [Radar Bot](https://github.com/Dennitsa0-0/Radar_Bot.git): Radar Bot может быть внешним наблюдателем и точкой раннего сигнала, а Smotritel - серверным пультом для проверки состояния, чтения логов и быстрых админских действий.

### Что умеет

- Показывает статус хоста: hostname, uptime, CPU, RAM, диск и ping.
- Показывает список Docker-контейнеров со статусом и uptime.
- Отдает обрезанные логи контейнеров.
- Перезапускает Docker-контейнеры с защитой от перезапуска самого Smotritel.
- Выполняет разбан Fail2Ban напрямую через Unix-сокет без `fail2ban-client` внутри контейнера.
- Запускает Telegram, Discord или обе платформы из одного event loop.
- Поддерживает интерфейс на русском и английском: `APP_LANG=ru` или `APP_LANG=en`.

### Связка с Radar Bot

Smotritel и Radar Bot лучше рассматривать как пару:

- Radar Bot - наблюдение, сигналы, внешняя логика оповещения.
- Smotritel - проверка сервера, Docker, логи, Fail2Ban и ручные действия администратора.

Практичный сценарий: Radar Bot замечает событие или проблему, оператор открывает Smotritel в Telegram/Discord, проверяет сервер, смотрит контейнеры и логи, при необходимости перезапускает сервис или снимает бан в Fail2Ban.

### Требования

- Linux-сервер с Docker Engine и Docker Compose plugin.
- Python на хосте не нужен, если запуск идет через Docker.
- Опционально: установленный и запущенный Fail2Ban.
- Опционально: Telegram bot token.
- Опционально: Discord bot token.

Нужен хотя бы один токен:

- `TG_BOT_TOKEN` для Telegram
- `DISCORD_BOT_TOKEN` для Discord

### Безопасность

Smotritel - админский инструмент. Относитесь к нему как к привилегированному сервису.

Контейнер монтирует:

- `/var/run/docker.sock`
- `/var/run/fail2ban/fail2ban.sock`
- `/hostfs/etc/hostname` через read-only mount `/hostfs`

Доступ на запись к Docker socket фактически дает контроль над хостом. Любой администратор бота сможет перезапускать контейнеры и читать логи. Храните токены приватно, строго задавайте списки admin ID и запускайте бота только для доверенных операторов.

Перезапуск контейнера Smotritel блокируется, чтобы избежать self-restart loop.

### Быстрый деплой

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

### Конфигурация

```env
# ==== SYSTEM SETTINGS ====
APP_LANG=ru
MONITOR_INTERVAL_HOURS=1
SMOTRITEL_CONTAINER_NAME=Smotritel

# ==== TELEGRAM CONFIG ====
TG_BOT_TOKEN=
TG_ADMIN_IDS=12345678,98765432

# ==== DISCORD CONFIG ====
DISCORD_BOT_TOKEN=
DISCORD_ADMIN_IDS=112233445566,778899

# ==== FAIL2BAN CONFIG ====
F2B_SOCK_PATH=/var/run/fail2ban/fail2ban.sock
```

Важно:

- `APP_LANG` поддерживает `en` и `ru`.
- `TG_ADMIN_IDS` и `DISCORD_ADMIN_IDS` задаются через запятую.
- Старые ключи `BOT_TOKEN` и `ADMIN_IDS` намеренно игнорируются. Используйте `TG_BOT_TOKEN` и `TG_ADMIN_IDS`.
- Если токен платформы пустой, платформа пропускается.
- Если оба токена пустые, приложение корректно завершится.

### Как получить admin ID

Telegram:

- Напишите боту вроде `@userinfobot` или посмотрите updates во время разработки.
- Добавьте numeric Telegram user ID в `TG_ADMIN_IDS`.

Discord:

- Включите Developer Mode в Discord.
- Нажмите правой кнопкой по пользователю и скопируйте user ID.
- Добавьте его в `DISCORD_ADMIN_IDS`.

### Проверка сокетов

Перед деплоем проверьте:

```bash
ls -l /var/run/docker.sock
ls -l /var/run/fail2ban/fail2ban.sock
```

Если Fail2Ban не установлен или не запущен, статус и Docker-функции могут работать, но разбан вернет аккуратную ошибку в боте.

### Эксплуатация

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

### Диагностика

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

### Разработка

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -e .[dev]
.venv\Scripts\python -m pytest
```

Smoke checks:

```bash
python -m compileall src tests bot.py
pytest
docker compose build
```

### Лицензия

Smotritel распространяется по Smotritel Non-Commercial License 1.0.

Код можно копировать, изменять и распространять для некоммерческого использования. Нельзя продавать код, брать плату за доступ к нему или использовать его как часть платного продукта, платного сервиса, SaaS, клиентской разработки/консалтинга или другой коммерческой активности без письменного разрешения правообладателя.

## English

Smotritel is a lightweight async DevOps informer for Linux servers. It exposes host status, Docker containers, logs, container restart controls, and Fail2Ban unban actions through Telegram and Discord.

The project works well on its own, but it is designed to be especially useful together with [Radar Bot](https://github.com/Dennitsa0-0/Radar_Bot.git): Radar Bot can act as the external watcher and early-signal layer, while Smotritel acts as the server control panel for status checks, logs, and quick admin actions.

### What It Does

- Shows host status: hostname, uptime, CPU, RAM, disk usage, and ping.
- Lists Docker containers with status and uptime.
- Shows trimmed container logs.
- Restarts Docker containers, with protection against restarting the Smotritel container itself.
- Runs Fail2Ban unban actions through the Fail2Ban Unix socket, without installing `fail2ban-client` inside the bot container.
- Runs Telegram, Discord, or both from the same event loop.
- Supports Russian and English UI strings: `APP_LANG=ru` or `APP_LANG=en`.

### Working With Radar Bot

Smotritel and Radar Bot are best treated as a pair:

- Radar Bot - monitoring, signals, and external alert logic.
- Smotritel - server status, Docker, logs, Fail2Ban, and manual admin actions.

A practical flow: Radar Bot notices an event or a problem, the operator opens Smotritel in Telegram/Discord, checks the server, reviews containers and logs, then restarts a service or unbans an IP when needed.

### Requirements

- Linux server with Docker Engine and Docker Compose plugin.
- Python is not required on the host when using Docker.
- Optional: Fail2Ban installed and running on the host.
- Optional: Telegram bot token.
- Optional: Discord bot token.

At least one platform token is required:

- `TG_BOT_TOKEN` for Telegram
- `DISCORD_BOT_TOKEN` for Discord

### Security Notice

Smotritel is an admin tool. Treat it like a privileged service.

The container mounts:

- `/var/run/docker.sock`
- `/var/run/fail2ban/fail2ban.sock`
- `/hostfs/etc/hostname` through the read-only `/hostfs` mount

Docker socket write access is effectively host-level control. Anyone who can use the bot as an admin can restart host containers and inspect logs. Keep bot tokens private, keep admin ID lists strict, and run it only for trusted operators.

The Docker restart action blocks the configured Smotritel container name to avoid self-restart loops.

### Quick Deploy

Clone the repository on the server:

```bash
git clone git@github.com:Dennitsa0-0/smotritel.git
cd smotritel
```

Create config:

```bash
cp .env.example .env
nano .env
```

Start:

```bash
docker compose up --build -d
docker compose logs -f
```

### Configuration

```env
# ==== SYSTEM SETTINGS ====
APP_LANG=en
MONITOR_INTERVAL_HOURS=1
SMOTRITEL_CONTAINER_NAME=Smotritel

# ==== TELEGRAM CONFIG ====
TG_BOT_TOKEN=
TG_ADMIN_IDS=12345678,98765432

# ==== DISCORD CONFIG ====
DISCORD_BOT_TOKEN=
DISCORD_ADMIN_IDS=112233445566,778899

# ==== FAIL2BAN CONFIG ====
F2B_SOCK_PATH=/var/run/fail2ban/fail2ban.sock
```

Notes:

- `APP_LANG` supports `en` and `ru`.
- `TG_ADMIN_IDS` and `DISCORD_ADMIN_IDS` are comma-separated numeric IDs.
- Old keys like `BOT_TOKEN` and `ADMIN_IDS` are intentionally ignored. Use `TG_BOT_TOKEN` and `TG_ADMIN_IDS`.
- If a platform token is empty, that platform is skipped.
- If both platform tokens are empty, the app exits cleanly.

### Getting Admin IDs

Telegram:

- Send a message to a bot such as `@userinfobot`, or inspect updates while developing.
- Put your numeric Telegram user ID into `TG_ADMIN_IDS`.

Discord:

- Enable Developer Mode in Discord.
- Right-click your user and copy the user ID.
- Put it into `DISCORD_ADMIN_IDS`.

### Socket Checks

Before deploying, check that sockets exist on the host:

```bash
ls -l /var/run/docker.sock
ls -l /var/run/fail2ban/fail2ban.sock
```

If Fail2Ban is not installed or not running, status and Docker features can still work, but Fail2Ban unban actions will return a muted error in the bot.

### Operations

Start or update:

```bash
docker compose up --build -d
```

View logs:

```bash
docker compose logs -f
```

Restart the bot:

```bash
docker compose restart smotritel
```

Stop:

```bash
docker compose down
```

Update from Git:

```bash
git pull
docker compose up --build -d
```

### Troubleshooting

No platform starts:

- Check that `.env` contains `TG_BOT_TOKEN` or `DISCORD_BOT_TOKEN`.
- Check logs with `docker compose logs -f`.

Telegram bot does not answer:

- Check `TG_BOT_TOKEN`.
- Check that your numeric user ID is in `TG_ADMIN_IDS`.
- Non-admin users are ignored silently.

Docker features fail:

- Check `/var/run/docker.sock` exists on the host.
- Check the compose volume mount.
- Check that Docker Engine is running.

Fail2Ban unban fails:

- Check that Fail2Ban is running on the host.
- Check `F2B_SOCK_PATH`.
- Check `/var/run/fail2ban/fail2ban.sock` permissions.

Wrong server name in status:

- In Docker, Smotritel first reads `/hostfs/etc/hostname`.
- If unavailable, it falls back to `/etc/hostname`, then `socket.gethostname()`, then `Server`.

### Local Development

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -e .[dev]
.venv\Scripts\python -m pytest
```

Smoke checks:

```bash
python -m compileall src tests bot.py
pytest
docker compose build
```

### License

Smotritel is source-available under the Smotritel Non-Commercial License 1.0.

You may copy, modify, and distribute the code for non-commercial use. You may not sell it, charge for access to it, or use it as part of a paid product, paid service, SaaS offering, consulting deliverable, or other commercial activity without prior written permission.

## Repository Hygiene

Never commit `.env`, `.venv`, IDE folders, caches, or generated package metadata. Commit `.env.example` instead.
