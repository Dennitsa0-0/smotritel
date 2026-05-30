from smotritel.platforms.discord.bot import RateLimiter


def test_rate_limiter() -> None:
    limiter = RateLimiter(cooldown_seconds=10)
    assert limiter.allow(1, "status")
    assert not limiter.allow(1, "status")
    assert limiter.allow(1, "docker")
