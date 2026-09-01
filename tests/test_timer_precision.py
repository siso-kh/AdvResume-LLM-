"""
Test Timer Precision Fix
Verifies that time.perf_counter() provides accurate timing measurements.
"""
import time
import pytest


class TestTimerPrecision:
    """Test suite for timer precision improvements."""

    def test_perf_counter_accuracy(self):
        """perf_counter should measure ~50ms sleep accurately."""
        start = time.perf_counter()
        time.sleep(0.05)  # 50ms sleep
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Allow 10% tolerance (45-55ms)
        assert 45 < elapsed_ms < 55, f"Expected ~50ms, got {elapsed_ms:.2f}ms"

    def test_perf_counter_vs_time_time(self):
        """perf_counter should be more precise than time.time for short durations."""
        # Measure same interval with both
        start_perf = time.perf_counter()
        start_time = time.time()
        time.sleep(0.01)  # 10ms
        end_perf = time.perf_counter()
        end_time = time.time()

        perf_ms = (end_perf - start_perf) * 1000
        time_ms = (end_time - start_time) * 1000

        # Both should be close to 10ms (allow wider tolerance for time.time)
        assert 8 < perf_ms < 12, f"perf_counter: expected ~10ms, got {perf_ms:.2f}ms"
        assert 8 < time_ms < 20, f"time.time: expected ~10ms, got {time_ms:.2f}ms"

    def test_perf_counter_resolution(self):
        """perf_counter should have sub-millisecond resolution."""
        # Measure very short duration
        times = []
        for _ in range(100):
            start = time.perf_counter()
            end = time.perf_counter()
            times.append((end - start) * 1000)

        # Average should be very small (< 0.1ms)
        avg_ms = sum(times) / len(times)
        assert avg_ms < 0.1, f"Resolution too low: {avg_ms:.4f}ms"
