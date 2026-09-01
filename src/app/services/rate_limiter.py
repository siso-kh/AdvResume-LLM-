"""
Rate Limiter
Token bucket algorithm for API rate limiting.
"""
import asyncio
import time
from typing import Optional


class RateLimiter:
    """
    Token bucket rate limiter.

    Controls the rate of API calls to prevent 429 errors.
    """

    def __init__(
        self,
        requests_per_second: float = 2.0,
        burst_size: int = 5,
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_second: Maximum requests per second
            burst_size: Maximum burst size (tokens in bucket)
        """
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size
        self.tokens = burst_size
        self.last_refill = time.time()
        self._lock = asyncio.Lock()

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.requests_per_second
        self.tokens = min(self.burst_size, self.tokens + tokens_to_add)
        self.last_refill = now

    async def acquire(self):
        """Wait until a token is available."""
        async with self._lock:
            while True:
                self._refill()
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                # Calculate wait time for next token
                wait_time = (1 - self.tokens) / self.requests_per_second
                await asyncio.sleep(wait_time)

    def try_acquire(self) -> bool:
        """Try to acquire a token without waiting."""
        self._refill()
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False

    def get_status(self) -> dict:
        """Get current rate limiter status."""
        self._refill()
        return {
            "tokens_available": int(self.tokens),
            "burst_size": self.burst_size,
            "requests_per_second": self.requests_per_second,
            "next_token_in": max(0, (1 - self.tokens) / self.requests_per_second),
        }


class SyncRateLimiter:
    """
    Synchronous rate limiter for non-async contexts.
    """

    def __init__(
        self,
        requests_per_second: float = 2.0,
        burst_size: int = 5,
    ):
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size
        self.tokens = burst_size
        self.last_refill = time.time()

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.requests_per_second
        self.tokens = min(self.burst_size, self.tokens + tokens_to_add)
        self.last_refill = now

    def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for a token to be available.

        Args:
            timeout: Maximum wait time in seconds (None = wait forever)

        Returns:
            True if token acquired, False if timeout
        """
        start_time = time.time()
        while True:
            self._refill()
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            if timeout and (time.time() - start_time) >= timeout:
                return False
            wait_time = (1 - self.tokens) / self.requests_per_second
            time.sleep(min(wait_time, 0.1))  # Sleep in small increments

    def try_acquire(self) -> bool:
        """Try to acquire a token without waiting."""
        self._refill()
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False
