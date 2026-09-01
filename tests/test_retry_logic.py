"""
Test Retry Logic with Exponential Backoff
Verifies that the LLM scorer retries failed API calls correctly.
"""
import time
import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app.services.llm_scorer import LLMScorer
from src.app.config import settings


class TestRetryLogic:
    """Test suite for retry logic with exponential backoff."""

    def setup_method(self):
        """Set up test fixtures."""
        self.scorer = LLMScorer()

    def test_retry_on_failure_then_success(self):
        """Should retry failed API calls and succeed on later attempt."""
        call_count = 0

        def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Simulated API failure")
            # Success on 3rd call
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = (
                '{"score": 75, "decision": "maybe", "reasoning": "Test"}'
            )
            return mock_response

        start = time.perf_counter()
        with patch.object(self.scorer.client.chat.completions, "create", side_effect=mock_create):
            result = self.scorer.score_candidate("Test CV text", "Test JD")
        elapsed = (time.perf_counter() - start) * 1000

        assert call_count == 3, f"Expected 3 API calls, got {call_count}"
        assert result.score == 75, f"Expected score 75, got {result.score}"
        assert result.decision == "maybe", f"Expected 'maybe', got {result.decision}"
        assert result.error is None, f"Expected no error, got {result.error}"
        # Should have backoff delays (1s + 2s = ~3s minimum)
        assert elapsed > 2000, f"Expected backoff delays, got {elapsed:.0f}ms"

    def test_retry_exhausted_returns_error(self):
        """Should return error result when all retries are exhausted."""
        call_count = 0

        def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("Persistent API failure")

        with patch.object(self.scorer.client.chat.completions, "create", side_effect=mock_create):
            result = self.scorer.score_candidate("Test CV text", "Test JD")

        assert call_count == settings.MAX_RETRIES, f"Expected {settings.MAX_RETRIES} calls, got {call_count}"
        assert result.score == 0, f"Expected score 0, got {result.score}"
        assert result.error is not None, "Expected error to be set"
        assert "Persistent API failure" in result.error

    def test_retry_count_matches_config(self):
        """Should respect MAX_RETRIES configuration."""
        call_count = 0

        def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("Test failure")

        with patch.object(self.scorer.client.chat.completions, "create", side_effect=mock_create):
            self.scorer.score_candidate("Test CV text", "Test JD")

        assert call_count == settings.MAX_RETRIES, (
            f"Expected {settings.MAX_RETRIES} retries, got {call_count}"
        )

    def test_successful_call_no_retry(self):
        """Should not retry on successful API call."""
        call_count = 0

        def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = (
                '{"score": 85, "decision": "interview", "reasoning": "Good fit"}'
            )
            return mock_response

        with patch.object(self.scorer.client.chat.completions, "create", side_effect=mock_create):
            result = self.scorer.score_candidate("Test CV text", "Test JD")

        assert call_count == 1, f"Expected 1 API call, got {call_count}"
        assert result.score == 85
        assert result.error is None
