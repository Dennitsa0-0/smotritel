from smotritel.core.docker_prov import sanitize_log_text
from smotritel.core.f2b_prov import parse_ip_input


def test_parse_ip_input() -> None:
    assert parse_ip_input("192.0.2.1, 2001:db8::1\nbad") == ["192.0.2.1", "2001:db8::1"]


def test_parse_ip_input_deduplicates() -> None:
    assert parse_ip_input("192.0.2.1 192.0.2.1") == ["192.0.2.1"]


def test_sanitize_log_text_strips_ansi_and_trims() -> None:
    text = "\x1b[31mred\x1b[0m" + "x" * 4000
    result = sanitize_log_text(text, max_chars=3500)
    assert "\x1b" not in result
    assert len(result) == 3500
