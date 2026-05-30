from types import SimpleNamespace

from smotritel.core.docker_prov import DockerProvider


class Containers:
    def get(self, name):
        return SimpleNamespace(restart=lambda: None, logs=lambda tail: b"hello")

    def list(self, all=True):
        return [
            SimpleNamespace(
                name="web",
                status="running",
                attrs={"State": {"StartedAt": "2026-05-30T00:00:00Z", "Health": {"Status": "healthy"}}},
            )
        ]


def test_docker_provider_blocks_self_restart() -> None:
    provider = DockerProvider("Smotritel", client=SimpleNamespace(containers=Containers()))
    result = provider._restart_container_sync("Smotritel")
    assert not result.ok


def test_docker_provider_status() -> None:
    provider = DockerProvider("Smotritel", client=SimpleNamespace(containers=Containers()))
    statuses = provider._get_containers_status_sync()
    assert statuses[0].name == "web"
    assert statuses[0].is_healthy
