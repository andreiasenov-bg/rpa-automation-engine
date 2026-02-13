"""Tests for workflow retry strategies."""

import asyncio
import pytest
from workflow.retry_strategies import (
    RetryStrategy,
    RetryPolicy,
    RetryAttempt,
    RETRY_PRESETS,
    execute_with_retry,
)


# ─── RetryStrategy creation ───

class TestRetryStrategyCreation:
    def test_none_strategy(self):
        s = RetryStrategy.none()
        assert s.policy == RetryPolicy.NONE
        assert s.max_retries == 0

    def test_fixed_strategy(self):
        s = RetryStrategy.fixed(max_retries=3, delay=5.0)
        assert s.policy == RetryPolicy.FIXED
        assert s.base_delay == 5.0
        assert s.jitter is False

    def test_exponential_strategy(self):
        s = RetryStrategy.exponential(max_retries=5, base_delay=1.0, max_delay=60.0)
        assert s.policy == RetryPolicy.EXPONENTIAL
        assert s.max_retries == 5
        assert s.jitter is True

    def test_linear_strategy(self):
        s = RetryStrategy.linear(max_retries=4, base_delay=2.0)
        assert s.policy == RetryPolicy.LINEAR
        assert s.base_delay == 2.0

    def test_from_dict(self):
        config = {
            'policy': 'exponential',
            'max_retries': 7,
            'base_delay': 0.5,
            'max_delay': 120.0,
            'jitter': True,
        }
        s = RetryStrategy.from_dict(config)
        assert s.policy == RetryPolicy.EXPONENTIAL
        assert s.max_retries == 7
        assert s.base_delay == 0.5

    def test_to_dict_roundtrip(self):
        original = RetryStrategy.exponential(max_retries=5)
        d = original.to_dict()
        restored = RetryStrategy.from_dict(d)
        assert restored.policy == original.policy
        assert restored.max_retries == original.max_retries
        assert restored.base_delay == original.base_delay


# ─── Delay computation ───

class TestDelayComputation:
    def test_none_delay(self):
        s = RetryStrategy.none()
        assert s.compute_delay(1) == 0.0

    def test_fixed_delay(self):
        s = RetryStrategy.fixed(delay=5.0)
        assert s.compute_delay(1) == 5.0
        assert s.compute_delay(3) == 5.0

    def test_exponential_delay_no_jitter(self):
        s = RetryStrategy.exponential(base_delay=1.0, jitter=False)
        assert s.compute_delay(1) == 1.0
        assert s.compute_delay(2) == 2.0
        assert s.compute_delay(3) == 4.0
        assert s.compute_delay(4) == 8.0

    def test_linear_delay(self):
        s = RetryStrategy.linear(base_delay=2.0)
        assert s.compute_delay(1) == 2.0
        assert s.compute_delay(2) == 4.0
        assert s.compute_delay(3) == 6.0

    def test_max_delay_cap(self):
        s = RetryStrategy.exponential(base_delay=10.0, max_delay=30.0, jitter=False)
        assert s.compute_delay(5) == 30.0  # 10 * 16 = 160, capped at 30

    def test_exponential_with_jitter_in_range(self):
        s = RetryStrategy.exponential(base_delay=10.0, jitter=True, max_delay=100.0)
        for _ in range(50):
            delay = s.compute_delay(1)
            # base=10, jitter_range=0.5 → between 5 and 15
            assert 5.0 <= delay <= 15.0


# ─── Should retry ───

class TestShouldRetry:
    def test_none_never_retries(self):
        s = RetryStrategy.none()
        assert s.should_retry(1) is False

    def test_exceeds_max_retries(self):
        s = RetryStrategy.fixed(max_retries=3)
        assert s.should_retry(3) is False
        assert s.should_retry(2) is True

    def test_no_error_always_retries(self):
        s = RetryStrategy.fixed(max_retries=5)
        assert s.should_retry(1, None) is True

    def test_timeout_error_retried(self):
        s = RetryStrategy.exponential()
        assert s.should_retry(1, TimeoutError("timeout")) is True

    def test_connection_error_retried(self):
        s = RetryStrategy.exponential()
        assert s.should_retry(1, ConnectionError("refused")) is True

    def test_specific_retryable_errors(self):
        s = RetryStrategy.exponential()
        s.retryable_errors = ['ValueError']
        assert s.should_retry(1, ValueError("bad")) is True
        assert s.should_retry(1, TypeError("wrong")) is False

    def test_transient_indicator_in_message(self):
        s = RetryStrategy.exponential()
        assert s.should_retry(1, Exception("HTTP 503 Service Unavailable")) is True
        assert s.should_retry(1, Exception("HTTP 429 Too Many Requests")) is True


# ─── Attempts ───

class TestAttempts:
    def test_none_returns_empty(self):
        s = RetryStrategy.none()
        assert s.attempts() == []

    def test_correct_number_of_attempts(self):
        s = RetryStrategy.fixed(max_retries=3, delay=1.0)
        attempts = s.attempts()
        assert len(attempts) == 3

    def test_attempt_is_last(self):
        s = RetryStrategy.fixed(max_retries=2, delay=1.0)
        attempts = s.attempts()
        assert attempts[0].is_last is False
        assert attempts[1].is_last is True


# ─── Presets ───

class TestPresets:
    def test_all_presets_exist(self):
        expected = {'none', 'conservative', 'aggressive', 'api_call', 'web_scraping', 'database', 'email'}
        assert set(RETRY_PRESETS.keys()) == expected

    def test_presets_are_valid(self):
        for name, strategy in RETRY_PRESETS.items():
            assert isinstance(strategy, RetryStrategy)
            assert strategy.max_retries >= 0


# ─── Execute with retry ───

class TestExecuteWithRetry:
    @pytest.mark.asyncio
    async def test_success_first_attempt(self):
        call_count = 0
        async def func():
            nonlocal call_count
            call_count += 1
            return 42

        result = await execute_with_retry(func, RetryStrategy.fixed(max_retries=3, delay=0.01))
        assert result == 42
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_failure(self):
        call_count = 0
        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("refused")
            return "ok"

        result = await execute_with_retry(func, RetryStrategy.fixed(max_retries=5, delay=0.01))
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exhausts_retries(self):
        async def func():
            raise TimeoutError("always timeout")

        with pytest.raises(TimeoutError):
            await execute_with_retry(func, RetryStrategy.fixed(max_retries=2, delay=0.01))

    @pytest.mark.asyncio
    async def test_no_retry_on_non_retryable(self):
        call_count = 0
        async def func():
            nonlocal call_count
            call_count += 1
            raise ValueError("not retryable")

        s = RetryStrategy.exponential(max_retries=5, base_delay=0.01)
        s.retryable_errors = ['TimeoutError']

        with pytest.raises(ValueError):
            await execute_with_retry(func, s)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_on_retry_callback(self):
        retries = []
        async def func():
            if len(retries) < 2:
                raise ConnectionError("fail")
            return "done"

        def on_retry(attempt, error, delay):
            retries.append(attempt)

        result = await execute_with_retry(
            func,
            RetryStrategy.fixed(max_retries=5, delay=0.01),
            on_retry=on_retry,
        )
        assert result == "done"
        assert retries == [1, 2]
