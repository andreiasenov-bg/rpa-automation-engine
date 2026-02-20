"""Tests for rate limiting middleware."""

import threading


from core.rate_limit import (
    SlidingWindowCounter,
    _classify_request,
    RATE_LIMITS,
)


class TestClassifyRequest:
    """Test request classification into rate limit groups."""

    def test_auth_endpoints(self):
        assert _classify_request("POST", "/api/v1/auth/login") == "auth"
        assert _classify_request("POST", "/api/v1/auth/register") == "auth"
        assert _classify_request("GET", "/api/v1/auth/me") == "auth"

    def test_ai_endpoints(self):
        assert _classify_request("POST", "/api/v1/ai/generate") == "ai"
        assert _classify_request("GET", "/api/v1/ai/models") == "ai"

    def test_write_methods(self):
        assert _classify_request("POST", "/api/v1/workflows") == "write"
        assert _classify_request("PUT", "/api/v1/workflows/123") == "write"
        assert _classify_request("PATCH", "/api/v1/workflows/123") == "write"
        assert _classify_request("DELETE", "/api/v1/workflows/123") == "write"

    def test_read_methods(self):
        assert _classify_request("GET", "/api/v1/workflows") == "read"
        assert _classify_request("GET", "/api/v1/executions") == "read"

    def test_default_fallback(self):
        assert _classify_request("OPTIONS", "/api/v1/workflows") == "default"
        assert _classify_request("HEAD", "/api/v1/health") == "default"


class TestSlidingWindowCounter:
    """Test the sliding window rate counter."""

    def test_first_request_allowed(self):
        counter = SlidingWindowCounter()
        allowed, count, limit, retry = counter.check_and_increment(
            "user:1", "read", 10, 60
        )
        assert allowed is True
        assert count == 1
        assert limit == 10
        assert retry == 0

    def test_within_limit(self):
        counter = SlidingWindowCounter()
        for i in range(5):
            allowed, count, limit, retry = counter.check_and_increment(
                "user:1", "read", 10, 60
            )
            assert allowed is True
            assert count == i + 1

    def test_exceeds_limit(self):
        counter = SlidingWindowCounter()
        # Exhaust the limit
        for _ in range(10):
            counter.check_and_increment("user:1", "read", 10, 60)

        # Next request should be rejected
        allowed, count, limit, retry = counter.check_and_increment(
            "user:1", "read", 10, 60
        )
        assert allowed is False
        assert retry > 0

    def test_different_keys_independent(self):
        counter = SlidingWindowCounter()
        for _ in range(10):
            counter.check_and_increment("user:1", "read", 10, 60)

        # Different user should still be allowed
        allowed, _, _, _ = counter.check_and_increment("user:2", "read", 10, 60)
        assert allowed is True

    def test_different_groups_independent(self):
        counter = SlidingWindowCounter()
        for _ in range(10):
            counter.check_and_increment("user:1", "read", 10, 60)

        # Same user, different group should still be allowed
        allowed, _, _, _ = counter.check_and_increment("user:1", "write", 60, 60)
        assert allowed is True

    def test_thread_safety(self):
        """Concurrent requests should not corrupt state."""
        counter = SlidingWindowCounter()
        results = []

        def make_requests():
            for _ in range(50):
                allowed, _, _, _ = counter.check_and_increment(
                    "user:1", "test", 200, 60
                )
                results.append(allowed)

        threads = [threading.Thread(target=make_requests) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All 200 should be allowed (4 threads * 50 = 200)
        assert len(results) == 200
        assert all(results)

    def test_cleanup_on_memory_bound(self):
        counter = SlidingWindowCounter()
        counter._max_keys = 10  # Low bound for testing

        for i in range(15):
            counter.check_and_increment(f"user:{i}", "read", 100, 60)

        # Should have cleaned up some keys
        assert len(counter._windows) <= 13  # 15 - 20% of 10 = ~13


class TestRateLimitsConfig:
    """Test rate limit configuration."""

    def test_all_groups_defined(self):
        assert "auth" in RATE_LIMITS
        assert "ai" in RATE_LIMITS
        assert "write" in RATE_LIMITS
        assert "read" in RATE_LIMITS
        assert "default" in RATE_LIMITS

    def test_auth_is_most_restrictive(self):
        auth_limit, _ = RATE_LIMITS["auth"]
        for group, (limit, _) in RATE_LIMITS.items():
            if group != "auth":
                assert auth_limit <= limit, f"Auth should be most restrictive but {group} has lower limit"

    def test_all_windows_positive(self):
        for group, (limit, window) in RATE_LIMITS.items():
            assert limit > 0, f"{group} limit must be positive"
            assert window > 0, f"{group} window must be positive"
