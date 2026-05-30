# Smotritel

Smotritel is a lightweight async DevOps informer for Linux servers. It exposes host metrics, Docker container status/logs/restart controls, and Fail2Ban unban actions through Telegram and Discord bots.

The project is intentionally small: core server logic lives separately from Telegram/Discord UI code, so it stays easy to audit before running it on a production host.

## What It Does

- Shows host status: hostname, uptime, CPU, RAM, disk usage, and ping.
- Lists Docker containers with status and uptime.
- Shows trimmed container logs.
- Restarts Docker containers, with protection against restarting the Smotritel container itself.
- Runs Fail2Ban unban actions through the Fail2Ban Unix socket, without installing `fail2ban-client` inside the bot container.
- Runs Telegram, Discord, or both from the same event loop.
- Supports English and Russian UI strings.

## Server Requirements

- Linux server with Docker Engine and Docker Compose plugin.
- Python is not required on the host when using Docker.
- Optional: Fail2Ban installed and running on the host.
- Optional: Discord bot token.
- Optional: Telegram bot token.

At least one platform token is required:

- `TG_BOT_TOKEN` for Telegram
- `DISCORD_BOT_TOKEN` for Discord

## Security Notice

Smotritel is an admin tool. Treat it like a privileged service.

The container mounts:

- `/var/run/docker.sock`
- `/var/run/fail2ban/fail2ban.sock`
- `/hostfs/etc/hostname` through the read-only `/hostfs` mount

Docker socket write access is effectively host-level control. Anyone who can use the bot as an admin can restart host containers and inspect logs. Keep bot tokens private, keep admin ID lists strict, and run it only for trusted operators.

The Docker restart action blocks the configured Smotritel container name to avoid self-restart loops.

## License

Smotritel is source-available under the Smotritel Non-Commercial License 1.0.

You may copy, modify, and distribute the code for non-commercial use. You may not sell it, charge for access to it, or use it as part of a paid product, paid service, SaaS offering, consulting deliverable, or other commercial activity without prior written permission.

## Quick Deploy

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

## Configuration

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

## Getting Admin IDs

Telegram:

- Send a message to a bot such as `@userinfobot`, or inspect updates while developing.
- Put your numeric Telegram user ID into `TG_ADMIN_IDS`.

Discord:

- Enable Developer Mode in Discord.
- Right-click your user and copy the user ID.
- Put it into `DISCORD_ADMIN_IDS`.

## Docker And Fail2Ban Sockets

Before deploying, check that sockets exist on the host:

```bash
ls -l /var/run/docker.sock
ls -l /var/run/fail2ban/fail2ban.sock
```

If Fail2Ban is not installed or not running, status and Docker features can still work, but Fail2Ban unban actions will return a muted error in the bot.

The compose file mounts Docker as `:rw` because restart support needs write access. Fail2Ban is also mounted as `:rw` because commands are sent over the socket.

## Operations

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

## Troubleshooting

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

## Local Development

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
