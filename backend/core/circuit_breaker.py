"""Circuit breaker pattern for resilient scraping.

Prevents hammering sites that are blocking us. After N consecutive
failures for a domain, the breaker opens and skips requests for
a cooldown period.
"""

import time
import logging
from collections import defaultdict
from typing import Optional

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Per-domain circuit breaker for HTTP/browser requests."""

    # Class-level state shared across all tasks
    _failures: dict = defaultdict(int)
    _last_failure: dict = defaultdict(float)
    _state: dict = defaultdict(lambda: "closed")  # closed, open, half-open

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 300,
        half_open_max: int = 1,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max = half_open_max

    def can_execute(self, domain: str) -> bool:
        """Check if requests to this domain are allowed."""
        state = self._state[domain]

        if state == "closed":
            return True

        if state == "open":
            elapsed = time.time() - self._last_failure[domain]
            if elapsed >= self.recovery_timeout:
                self._state[domain] = "half-open"
                logger.info(f"Circuit half-open for {domain} after {elapsed:.0f}s cooldown")
                return True
            logger.warning(
                f"Circuit OPEN for {domain}, "
                f"{self.recovery_timeout - elapsed:.0f}s remaining"
            )
            return False

        # half-open: allow limited requests
        return True

    def record_success(self, domain: str):
        """Record a successful request — reset the breaker."""
        if self._state[domain] != "closed":
            logger.info(f"Circuit CLOSED for {domain} after successful request")
        self._failures[domain] = 0
        self._state[domain] = "closed"

    def record_failure(self, domain: str, error: Optional[str] = None):
        """Record a failed request — may trip the breaker."""
        self._failures[domain] += 1
        self._last_failure[domain] = time.time()

        if self._failures[domain] >= self.failure_threshold:
            self._state[domain] = "open"
            logger.error(
                f"Circuit OPENED for {domain} after "
                f"{self._failures[domain]} consecutive failures. "
                f"Cooldown: {self.recovery_timeout}s. Last error: {error}"
            )

    def get_status(self) -> dict:
        """Get status of all tracked domains."""
        result = {}
        for domain in set(list(self._failures.keys()) + list(self._state.keys())):
            result[domain] = {
                "state": self._state[domain],
                "failures": self._failures[domain],
                "last_failure": self._last_failure.get(domain),
            }
        return result

    def reset(self, domain: Optional[str] = None):
        """Reset breaker for a domain or all domains."""
        if domain:
            self._failures.pop(domain, None)
            self._last_failure.pop(domain, None)
            self._state.pop(domain, None)
        else:
            self._failures.clear()
            self._last_failure.clear()
            self._state.clear()


# Global singleton
circuit_breaker = CircuitBreaker()
