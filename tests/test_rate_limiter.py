"""
Test Rate Limiter
Verifies token bucket rate limiting behavior.
"""
import asyncio
import time
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app.services.rate_limiter import RateLimiter, SyncRateLimiter


class TestSyncRateLimiter:
    """Test suite for synchronous rate limiter."""

    def test_try_acquire_within_burst(self):
        """Should acquire tokens within burst size."""
        limiter = SyncRateLimiter(requests_per_second=10.0, burst_size=5)

        # Should acquire 5 tokens immediately
        for _ in range(5):
            assert limiter.try_acquire() is True

        # 6th should fail
        assert limiter.try_acquire() is False

    def test_acquire_with_timeout(self):
        """Should wait and acquire token after refill."""
        limiter = SyncRateLimiter(requests_per_second=100.0, burst_size=1)

        # Exhaust burst
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is False

        # Should acquire after short wait
        start = time.perf_counter()
        acquired = limiter.acquire(timeout=0.1)
        elapsed = time.perf_counter() - start

        assert acquired is True
        assert elapsed < 0.2  # Should be quick

    def test_acquire_timeout_returns_false(self):
        """Should return False on timeout."""
        limiter = SyncRateLimiter(requests_per_second=1.0, burst_size=1)

        # Exhaust burst
        limiter.try_acquire()

        # Should timeout
        acquired = limiter.acquire(timeout=0.05)
        assert acquired is False


class TestAsyncRateLimiter:
    """Test suite for asynchronous rate limiter."""

    @pytest.mark.asyncio
    async def test_acquire_respects_rate_limit(self):
        """Should respect rate limit over time."""
        limiter = RateLimiter(requests_per_second=10.0, burst_size=2)

        # First 2 should be instant
        start = time.perf_counter()
        await limiter.acquire()
        await limiter.acquire()
        first_two = time.perf_counter() - start

        # Third should wait ~100ms (1/10 seconds)
        start = time.perf_counter()
        await limiter.acquire()
        third_time = time.perf_counter() - start

        assert first_two < 0.05  # Instant
        assert third_time > 0.05  # Had to wait

    @pytest.mark.asyncio
    async def test_concurrent_acquire(self):
        """Should handle concurrent acquire calls."""
        limiter = RateLimiter(requests_per_second=20.0, burst_size=5)

        results = []
        async def acquire_and_record():
            await limiter.acquire()
            results.append(time.perf_counter())

        # Run 5 concurrent acquires
        await asyncio.gather(*[acquire_and_record() for _ in range(5)])

        # All should complete
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_get_status(self):
        """Should report correct status."""
        limiter = RateLimiter(requests_per_second=10.0, burst_size=5)

        status = limiter.get_status()
        assert status["tokens_available"] == 5
        assert status["burst_size"] == 5
        assert status["requests_per_second"] == 10.0
