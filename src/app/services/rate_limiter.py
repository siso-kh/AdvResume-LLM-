"""
Rate Limiter
Token bucket algorithm for API rate limiting with daily reset.
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional


def get_seconds_until_midnight() -> float:
    """Calculate seconds until next midnight."""
    now = datetime.now()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return (midnight - now).total_seconds()


def get_days_since_epoch() -> int:
    """Get current day number (for daily reset tracking)."""
    return (datetime.now() - datetime(1970, 1, 1)).days


class RateLimiter:
    """
    Token bucket rate limiter with daily reset.

    Controls the rate of API calls to prevent 429 errors.
    Resets token bucket daily at midnight.
    """

    def __init__(
        self,
        requests_per_second: float = 2.0,
        burst_size: int = 5,
        daily_reset: bool = True,
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_second: Maximum requests per second
            burst_size: Maximum burst size (tokens in bucket)
            daily_reset: Reset token bucket daily at midnight
        """
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size
        self.daily_reset = daily_reset
        self.tokens = burst_size
        self.last_refill = time.time()
        self.current_day = get_days_since_epoch()
        self._lock = asyncio.Lock()

    def _check_daily_reset(self):
        """Check if we need to reset for a new day."""
        if not self.daily_reset:
            return
        
        new_day = get_days_since_epoch()
        if new_day != self.current_day:
            print(f"  [Rate Limiter] Daily reset: {self.current_day} -> {new_day}")
            self.tokens = self.burst_size  # Full burst on new day
            self.current_day = new_day

    def _refill(self):
        """Refill tokens based on elapsed time."""
        self._check_daily_reset()
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
            "daily_reset": self.daily_reset,
            "current_day": self.current_day,
            "seconds_until_midnight": get_seconds_until_midnight(),
        }


class SyncRateLimiter:
    """
    Synchronous rate limiter for non-async contexts with daily reset.
    """

    def __init__(
        self,
        requests_per_second: float = 2.0,
        burst_size: int = 5,
        daily_reset: bool = True,
    ):
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size
        self.daily_reset = daily_reset
        self.tokens = burst_size
        self.last_refill = time.time()
        self.current_day = get_days_since_epoch()

    def _check_daily_reset(self):
        """Check if we need to reset for a new day."""
        if not self.daily_reset:
            return
        
        new_day = get_days_since_epoch()
        if new_day != self.current_day:
            print(f"  [Rate Limiter] Daily reset: {self.current_day} -> {new_day}")
            self.tokens = self.burst_size
            self.current_day = new_day

    def _refill(self):
        """Refill tokens based on elapsed time."""
        self._check_daily_reset()
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

    def get_status(self) -> dict:
        """Get current rate limiter status."""
        self._refill()
        return {
            "tokens_available": int(self.tokens),
            "burst_size": self.burst_size,
            "requests_per_second": self.requests_per_second,
            "next_token_in": max(0, (1 - self.tokens) / self.requests_per_second),
            "daily_reset": self.daily_reset,
            "current_day": self.current_day,
            "seconds_until_midnight": get_seconds_until_midnight(),
        }
