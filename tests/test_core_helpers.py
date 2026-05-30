from smotritel.core.docker_prov import sanitize_log_text
from smotritel.core.dto import ContainerStatus
from smotritel.core.f2b_prov import parse_ip_input
from smotritel.platforms.formatting import container_at_page_index, container_page, page_count, sorted_containers


def test_parse_ip_input() -> None:
    assert parse_ip_input("192.0.2.1, 2001:db8::1\nbad") == ["192.0.2.1", "2001:db8::1"]


def test_parse_ip_input_deduplicates() -> None:
    assert parse_ip_input("192.0.2.1 192.0.2.1") == ["192.0.2.1"]


def test_sanitize_log_text_strips_ansi_and_trims() -> None:
    text = "\x1b[31mred\x1b[0m" + "x" * 4000
    result = sanitize_log_text(text, max_chars=3500)
    assert "\x1b" not in result
    assert len(result) == 3500


def test_container_pagination_uses_stable_name_order() -> None:
    containers = [
        ContainerStatus("zeta", "running", "1h"),
        ContainerStatus("Alpha", "running", "1h"),
        ContainerStatus("beta", "exited", "2h"),
    ]

    assert [container.name for container in sorted_containers(containers)] == ["Alpha", "beta", "zeta"]
    assert page_count(len(containers), 2) == 2
    items, page, total_pages = container_page(containers, 0, 2)

    assert page == 0
    assert total_pages == 2
    assert [container.name for container in items] == ["Alpha", "beta"]
    assert container_at_page_index(containers, 1, 0, 2).name == "zeta"
