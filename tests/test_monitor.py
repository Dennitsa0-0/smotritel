from types import SimpleNamespace

from smotritel.core.monitor import SystemMonitor


def test_monitor_collect_with_mocked_psutil(monkeypatch) -> None:
    monitor = SystemMonitor(hostname_files=())
    monkeypatch.setattr("smotritel.core.monitor.psutil.cpu_percent", lambda interval: 12.5)
    monkeypatch.setattr(
        "smotritel.core.monitor.psutil.virtual_memory",
        lambda: SimpleNamespace(total=8 * 1024**3, used=3 * 1024**3, percent=37.5),
    )
    monkeypatch.setattr(
        "smotritel.core.monitor.psutil.disk_usage",
        lambda path: SimpleNamespace(total=100 * 1024**3, used=40 * 1024**3, percent=40.0),
    )
    monkeypatch.setattr("smotritel.core.monitor.psutil.boot_time", lambda: 0)
    monkeypatch.setattr("smotritel.core.monitor.socket.gethostname", lambda: "prod-01")
    monkeypatch.setattr(monitor, "_ping", lambda: "1 ms")

    status = monitor._collect()

    assert status.cpu_percent == 12.5
    assert status.host_name == "prod-01"
    assert status.ram_total_gb == 8
    assert status.ping == "1 ms"
