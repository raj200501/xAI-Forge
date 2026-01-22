from __future__ import annotations

import random
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_s: float = 0.2
    max_delay_s: float = 2.0
    jitter: float = 0.1

    def backoff(self, attempt: int) -> float:
        raw = min(self.max_delay_s, self.base_delay_s * (2 ** (attempt - 1)))
        return raw + random.uniform(0, self.jitter)


@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    reset_timeout_s: float = 5.0
    failures: int = 0
    opened_at: float | None = None

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.opened_at = time.time()

    def allow(self) -> bool:
        if self.opened_at is None:
            return True
        if time.time() - self.opened_at >= self.reset_timeout_s:
            self.failures = 0
            self.opened_at = None
            return True
        return False
