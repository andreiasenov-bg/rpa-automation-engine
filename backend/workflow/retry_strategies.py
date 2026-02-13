"""Workflow execution retry strategies.

Provides configurable retry policies for workflow steps:
- Fixed delay
- Exponential backoff (with optional jitter)
- Linear backoff
- Custom retry conditions based on error type

Usage:
    strategy = RetryStrategy.exponential(max_retries=5, base_delay=1.0, max_delay=60.0)
    for attempt in strategy:
        try:
            result = await execute_step(step)
            break
        except RetryableError:
            await attempt.wait()
"""

import asyncio
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, AsyncIterator


class RetryPolicy(str, Enum):
    """Available retry policies."""
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    NONE = "none"


@dataclass
class RetryAttempt:
    """Represents a single retry attempt with computed delay."""
    number: int
    delay: float
    max_retries: int
    started_at: float = field(default_factory=time.monotonic)

    @property
    def is_last(self) -> bool:
        return self.number >= self.max_retries

    async def wait(self) -> None:
        """Wait for the computed delay before next attempt."""
        if self.delay > 0:
            await asyncio.sleep(self.delay)


@dataclass
class RetryStrategy:
    """Configurable retry strategy for workflow step execution."""
    policy: RetryPolicy
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 300.0
    jitter: bool = True
    jitter_range: float = 0.5
    retryable_errors: list[str] = field(default_factory=list)
    retry_on_timeout: bool = True
    retry_on_connection_error: bool = True

    @classmethod
    def none(cls) -> 'RetryStrategy':
        """No retries — fail immediately."""
        return cls(policy=RetryPolicy.NONE, max_retries=0)

    @classmethod
    def fixed(cls, max_retries: int = 3, delay: float = 5.0) -> 'RetryStrategy':
        """Fixed delay between retries."""
        return cls(
            policy=RetryPolicy.FIXED,
            max_retries=max_retries,
            base_delay=delay,
            jitter=False,
        )

    @classmethod
    def exponential(
        cls,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
    ) -> 'RetryStrategy':
        """Exponential backoff with optional jitter."""
        return cls(
            policy=RetryPolicy.EXPONENTIAL,
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
            jitter=jitter,
        )

    @classmethod
    def linear(
        cls,
        max_retries: int = 5,
        base_delay: float = 2.0,
        max_delay: float = 30.0,
    ) -> 'RetryStrategy':
        """Linear backoff: delay = base_delay * attempt_number."""
        return cls(
            policy=RetryPolicy.LINEAR,
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
            jitter=False,
        )

    @classmethod
    def from_dict(cls, config: dict) -> 'RetryStrategy':
        """Create strategy from a workflow step configuration dict."""
        policy = config.get('policy', 'exponential')
        return cls(
            policy=RetryPolicy(policy),
            max_retries=config.get('max_retries', 3),
            base_delay=config.get('base_delay', 1.0),
            max_delay=config.get('max_delay', 300.0),
            jitter=config.get('jitter', True),
            jitter_range=config.get('jitter_range', 0.5),
            retryable_errors=config.get('retryable_errors', []),
            retry_on_timeout=config.get('retry_on_timeout', True),
            retry_on_connection_error=config.get('retry_on_connection_error', True),
        )

    def to_dict(self) -> dict:
        """Serialize to dict for storage in workflow definition."""
        return {
            'policy': self.policy.value,
            'max_retries': self.max_retries,
            'base_delay': self.base_delay,
            'max_delay': self.max_delay,
            'jitter': self.jitter,
            'jitter_range': self.jitter_range,
            'retryable_errors': self.retryable_errors,
            'retry_on_timeout': self.retry_on_timeout,
            'retry_on_connection_error': self.retry_on_connection_error,
        }

    def compute_delay(self, attempt: int) -> float:
        """Compute the delay for a given attempt number (1-based)."""
        if self.policy == RetryPolicy.NONE:
            return 0.0

        if self.policy == RetryPolicy.FIXED:
            delay = self.base_delay
        elif self.policy == RetryPolicy.EXPONENTIAL:
            delay = self.base_delay * (2 ** (attempt - 1))
        elif self.policy == RetryPolicy.LINEAR:
            delay = self.base_delay * attempt
        else:
            delay = self.base_delay

        # Apply max cap
        delay = min(delay, self.max_delay)

        # Apply jitter
        if self.jitter and delay > 0:
            jitter_amount = delay * self.jitter_range
            delay = delay + random.uniform(-jitter_amount, jitter_amount)
            delay = max(0.0, delay)

        return round(delay, 3)

    def should_retry(self, attempt: int, error: Optional[Exception] = None) -> bool:
        """Determine if we should retry based on attempt number and error type."""
        if self.policy == RetryPolicy.NONE:
            return False

        if attempt >= self.max_retries:
            return False

        if error is None:
            return True

        error_name = type(error).__name__

        # Check specific retryable errors
        if self.retryable_errors:
            return error_name in self.retryable_errors

        # Default: retry on timeout and connection errors
        timeout_errors = {'TimeoutError', 'asyncio.TimeoutError', 'ConnectionTimeout', 'ReadTimeout'}
        connection_errors = {'ConnectionError', 'ConnectionRefusedError', 'ConnectionResetError', 'OSError'}

        if self.retry_on_timeout and error_name in timeout_errors:
            return True
        if self.retry_on_connection_error and error_name in connection_errors:
            return True

        # Retry on generic transient errors
        transient_indicators = ['timeout', 'connection', 'temporary', '503', '429', '502', '504']
        error_str = str(error).lower()
        return any(ind in error_str for ind in transient_indicators)

    def attempts(self) -> list[RetryAttempt]:
        """Generate list of retry attempts with pre-computed delays."""
        if self.policy == RetryPolicy.NONE:
            return []
        return [
            RetryAttempt(
                number=i,
                delay=self.compute_delay(i),
                max_retries=self.max_retries,
            )
            for i in range(1, self.max_retries + 1)
        ]


# ─── Preset strategies ───

RETRY_PRESETS: dict[str, RetryStrategy] = {
    'none': RetryStrategy.none(),
    'conservative': RetryStrategy.exponential(max_retries=3, base_delay=2.0, max_delay=30.0),
    'aggressive': RetryStrategy.exponential(max_retries=7, base_delay=0.5, max_delay=120.0),
    'api_call': RetryStrategy.exponential(max_retries=5, base_delay=1.0, max_delay=60.0),
    'web_scraping': RetryStrategy.exponential(max_retries=4, base_delay=3.0, max_delay=90.0),
    'database': RetryStrategy.fixed(max_retries=3, delay=2.0),
    'email': RetryStrategy.linear(max_retries=3, base_delay=10.0, max_delay=60.0),
}


async def execute_with_retry(
    func: Callable,
    strategy: RetryStrategy,
    *args,
    on_retry: Optional[Callable] = None,
    **kwargs,
):
    """Execute a function with the given retry strategy.

    Args:
        func: Async callable to execute.
        strategy: RetryStrategy instance.
        on_retry: Optional callback(attempt, error, delay) called before each retry.

    Returns:
        The result of func(*args, **kwargs).

    Raises:
        The last exception if all retries are exhausted.
    """
    last_error: Optional[Exception] = None
    attempt = 0

    while True:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_error = e
            attempt += 1

            if not strategy.should_retry(attempt, e):
                raise

            delay = strategy.compute_delay(attempt)

            if on_retry:
                try:
                    await on_retry(attempt, e, delay) if asyncio.iscoroutinefunction(on_retry) else on_retry(attempt, e, delay)
                except Exception:
                    pass  # Don't let callback errors break retry logic

            await asyncio.sleep(delay)

    # Should never reach here, but just in case
    if last_error:
        raise last_error
