from pm_os.web.login_security import LoginRateLimiter, resolve_client_ip


def test_client_ip_ignores_forwarded_header_without_trusted_proxy():
    assert (
        resolve_client_ip(
            "203.0.113.10",
            "198.51.100.5",
            trusted_proxy_count=0,
        )
        == "203.0.113.10"
    )


def test_client_ip_selects_address_before_trusted_proxy_chain():
    assert (
        resolve_client_ip(
            "10.0.0.3",
            "198.51.100.5, 10.0.0.2",
            trusted_proxy_count=2,
        )
        == "198.51.100.5"
    )


def test_client_ip_falls_back_when_proxy_header_is_invalid_or_too_short():
    assert resolve_client_ip("203.0.113.10", "not-an-ip", 1) == "203.0.113.10"
    assert resolve_client_ip("203.0.113.10", "198.51.100.5", 2) == "203.0.113.10"


def test_rate_limiter_counts_only_recorded_failures():
    limiter = LoginRateLimiter(max_attempts=2)

    assert not limiter.is_blocked("client")
    assert not limiter.is_blocked("client")
    limiter.record_failure("client")
    assert not limiter.is_blocked("client")
    limiter.record_failure("client")
    assert limiter.is_blocked("client")


def test_rate_limiter_reset_allows_login_after_success():
    limiter = LoginRateLimiter(max_attempts=1)
    limiter.record_failure("client")
    assert limiter.is_blocked("client")

    limiter.reset("client")

    assert not limiter.is_blocked("client")


def test_rate_limiter_expires_old_failures():
    now = [100.0]
    limiter = LoginRateLimiter(
        max_attempts=1,
        window_seconds=30,
        clock=lambda: now[0],
    )
    limiter.record_failure("client")
    assert limiter.is_blocked("client")

    now[0] = 131.0

    assert not limiter.is_blocked("client")


def test_rate_limiter_bounds_tracked_clients():
    limiter = LoginRateLimiter(max_clients=2)
    limiter.record_failure("oldest")
    limiter.record_failure("newer")
    limiter.record_failure("newest")

    assert "oldest" not in limiter._failures
    assert list(limiter._failures) == ["newer", "newest"]
