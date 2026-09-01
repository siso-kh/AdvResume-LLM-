"""
Test Token Usage Tracking
Verifies token tracking, budget management, and cost calculation.
"""
import pytest
from unittest.mock import MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app.services.token_tracker import TokenTracker


class TestTokenTracker:
    """Test suite for token usage tracking."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tracker = TokenTracker(daily_budget=7_000_000)

    def _mock_response(self, prompt_tokens: int, completion_tokens: int):
        """Create a mock API response."""
        response = MagicMock()
        response.usage.prompt_tokens = prompt_tokens
        response.usage.completion_tokens = completion_tokens
        return response

    def test_record_single_request(self):
        """Should record single request correctly."""
        response = self._mock_response(1000, 500)
        record = self.tracker.record(response, "mistral-large")

        assert record.prompt_tokens == 1000
        assert record.completion_tokens == 500
        assert record.total_tokens == 1500
        assert record.model == "mistral-large"
        assert record.cost > 0

    def test_record_multiple_requests(self):
        """Should accumulate totals across requests."""
        for _ in range(3):
            response = self._mock_response(1000, 500)
            self.tracker.record(response, "mistral-large")

        summary = self.tracker.get_summary()
        assert summary["total_prompt_tokens"] == 3000
        assert summary["total_completion_tokens"] == 1500
        assert summary["total_tokens"] == 4500
        assert summary["requests_count"] == 3

    def test_budget_check_ok(self):
        """Should report OK when within budget."""
        response = self._mock_response(100_000, 50_000)
        self.tracker.record(response, "mistral-large")

        is_ok, message = self.tracker.check_budget()
        assert is_ok is True
        assert "OK" in message

    def test_budget_check_warning(self):
        """Should warn when budget usage > 80%."""
        response = self._mock_response(6_000_000, 500_000)
        self.tracker.record(response, "mistral-large")

        is_ok, message = self.tracker.check_budget()
        assert is_ok is True
        assert "WARNING" in message

    def test_budget_check_critical(self):
        """Should flag critical when budget usage > 95%."""
        response = self._mock_response(6_800_000, 500_000)
        self.tracker.record(response, "mistral-large")

        is_ok, message = self.tracker.check_budget()
        assert is_ok is False
        assert "CRITICAL" in message

    def test_cost_calculation(self):
        """Should calculate cost correctly for known models."""
        response = self._mock_response(1_000_000, 1_000_000)
        record = self.tracker.record(response, "mistral-large")

        # mistral-large: $2/M prompt, $6/M completion
        expected_cost = 2.0 + 6.0  # $8.00
        assert record.cost == pytest.approx(expected_cost, rel=0.01)

    def test_save_and_load(self, tmp_path):
        """Should save and load usage history."""
        response = self._mock_response(1000, 500)
        self.tracker.record(response, "mistral-large")

        save_path = tmp_path / "usage.json"
        self.tracker.save(str(save_path))

        assert save_path.exists()
        import json
        with open(save_path) as f:
            data = json.load(f)

        assert "summary" in data
        assert "history" in data
        assert len(data["history"]) == 1
