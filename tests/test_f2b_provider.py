import asyncio

from smotritel.core.f2b_prov import Fail2BanProvider


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.commands = []

    async def send(self, command):
        self.commands.append(command)
        return self.response


def test_f2b_unban_all() -> None:
    client = FakeClient((0, "1"))
    provider = Fail2BanProvider(client=client)
    result = asyncio.run(provider.unban_all())
    assert result.ok
    assert client.commands == [["unban", "--all"]]


def test_f2b_unban_ips() -> None:
    client = FakeClient((0, "done"))
    provider = Fail2BanProvider(client=client)
    result = asyncio.run(provider.unban_ips(["192.0.2.1"]))
    assert result.ok
    assert client.commands == [["unban", "192.0.2.1"]]
