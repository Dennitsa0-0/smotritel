from __future__ import annotations

import asyncio
import ipaddress
import pickle
import re
from dataclasses import dataclass
from typing import Any

from .dto import ProviderResult

END_MARKER = b"<F2B_END_COMMAND>"
CLOSE_MARKER = b"<F2B_CLOSE_COMMAND>"


def parse_ip_input(raw: str) -> list[str]:
    ips: list[str] = []
    for token in re.split(r"[\s,;]+", raw.strip()):
        if not token:
            continue
        try:
            ips.append(str(ipaddress.ip_address(token)))
        except ValueError:
            continue
    return list(dict.fromkeys(ips))


@dataclass
class Fail2BanSocketClient:
    sock_path: str
    timeout: float = 5.0

    async def send(self, command: list[Any]) -> Any:
        reader, writer = await asyncio.wait_for(asyncio.open_unix_connection(self.sock_path), self.timeout)
        try:
            payload = pickle.dumps([self._convert(item) for item in command], pickle.HIGHEST_PROTOCOL)
            writer.write(payload + END_MARKER)
            await asyncio.wait_for(writer.drain(), self.timeout)
            response = await self._read_response(reader)
            return pickle.loads(response)
        finally:
            writer.write(CLOSE_MARKER + END_MARKER)
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def _read_response(self, reader: asyncio.StreamReader) -> bytes:
        data = b""
        while END_MARKER not in data:
            chunk = await asyncio.wait_for(reader.read(32768), self.timeout)
            if not chunk:
                break
            data += chunk
        return data.replace(END_MARKER, b"")

    @staticmethod
    def _convert(value: Any) -> Any:
        if isinstance(value, (str, bool, int, float, list, dict, set)):
            return value
        return str(value)


class Fail2BanProvider:
    def __init__(self, sock_path: str = "/var/run/fail2ban/fail2ban.sock", client: Fail2BanSocketClient | None = None) -> None:
        self.client = client or Fail2BanSocketClient(sock_path)

    async def unban_all(self) -> ProviderResult:
        return await self._send(["unban", "--all"])

    async def unban_ips(self, ips: list[str]) -> ProviderResult:
        valid_ips = [str(ipaddress.ip_address(ip)) for ip in ips]
        if not valid_ips:
            return ProviderResult(False, "No valid IP addresses found.")
        return await self._send(["unban", *valid_ips])

    async def _send(self, command: list[str]) -> ProviderResult:
        try:
            response = await self.client.send(command)
            code, payload = self._normalize_response(response)
            if code == 0:
                return ProviderResult(True, str(payload))
            return ProviderResult(False, "Fail2Ban command failed.", {"error": str(payload)})
        except Exception as exc:
            return ProviderResult(False, "Fail2Ban is unavailable.", {"error": str(exc)})

    @staticmethod
    def _normalize_response(response: Any) -> tuple[int, Any]:
        if isinstance(response, tuple) and len(response) == 2:
            return int(response[0]), response[1]
        return 0, response
