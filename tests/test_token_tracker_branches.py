"""
Tests for Uncovered Branches in Token Tracker
Tests print_summary and edge cases.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app.services.token_tracker import TokenTracker


class TestTokenTrackerBranches:
    """Test uncovered branches in token tracker."""

    def setup_method(self):
        self.tracker = TokenTracker(daily_budget=7_000_000)

    def _mock_response(self, prompt_tokens: int, completion_tokens: int):
        response = MagicMock()
        response.usage.prompt_tokens = prompt_tokens
        response.usage.completion_tokens = completion_tokens
        return response

    def test_print_summary(self, capsys):
        """Should print summary without errors."""
        response = self._mock_response(1000, 500)
        self.tracker.record(response, "mistral-large")

        self.tracker.print_summary()

        captured = capsys.readouterr()
        assert "TOKEN USAGE SUMMARY" in captured.out
        assert "Prompt tokens:" in captured.out
        assert "Completion tokens:" in captured.out
        assert "Total cost:" in captured.out

    def test_print_summary_empty(self, capsys):
        """Should print summary even with no data."""
        self.tracker.print_summary()

        captured = capsys.readouterr()
        assert "TOKEN USAGE SUMMARY" in captured.out
        assert "Prompt tokens:" in captured.out

    def test_budget_check_exact_80_percent(self):
        """Should warn at exactly 80%."""
        response = self._mock_response(5_600_000, 500_000)  # 80% of 7M
        self.tracker.record(response, "mistral-large")

        is_ok, message = self.tracker.check_budget()
        assert is_ok is True
        assert "WARNING" in message

    def test_budget_check_exact_95_percent(self):
        """Should flag critical at exactly 95%."""
        response = self._mock_response(6_650_000, 500_000)  # 95% of 7M
        self.tracker.record(response, "mistral-large")

        is_ok, message = self.tracker.check_budget()
        assert is_ok is False
        assert "CRITICAL" in message

    def test_unknown_model_cost(self):
        """Should use default cost for unknown models."""
        response = self._mock_response(1_000_000, 1_000_000)
        record = self.tracker.record(response, "unknown-model-xyz")

        # Default: $1/M prompt, $3/M completion
        expected_cost = 1.0 + 3.0  # $4.00
        assert record.cost == pytest.approx(expected_cost, rel=0.01)

    def test_free_model_cost(self):
        """Should track zero cost for free models."""
        response = self._mock_response(1_000_000, 1_000_000)
        record = self.tracker.record(response, "deepseek-v4-flash")

        assert record.cost == 0.0

    def test_get_summary_values(self):
        """Should return correct summary values."""
        response = self._mock_response(1000, 500)
        self.tracker.record(response, "mistral-large")

        summary = self.tracker.get_summary()
        assert summary["total_prompt_tokens"] == 1000
        assert summary["total_completion_tokens"] == 500
        assert summary["total_tokens"] == 1500
        assert summary["requests_count"] == 1
        assert summary["budget_remaining"] == 7_000_000 - 1000
        # Check budget percentage is approximately correct (allow rounding)
        expected_percent = 1000 / 7_000_000 * 100
        assert abs(summary["budget_used_percent"] - expected_percent) < 0.1

    def test_multiple_requests_accumulation(self):
        """Should accumulate across multiple requests."""
        for _ in range(5):
            response = self._mock_response(1000, 500)
            self.tracker.record(response, "mistral-large")

        summary = self.tracker.get_summary()
        assert summary["total_prompt_tokens"] == 5000
        assert summary["total_completion_tokens"] == 2500
        assert summary["requests_count"] == 5

    def test_history_tracking(self):
        """Should track request history."""
        response = self._mock_response(1000, 500)
        self.tracker.record(response, "mistral-large")

        assert len(self.tracker.history) == 1
        assert self.tracker.history[0].model == "mistral-large"
        assert self.tracker.history[0].prompt_tokens == 1000
