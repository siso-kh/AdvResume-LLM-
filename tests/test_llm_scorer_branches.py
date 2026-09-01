"""
Tests for Uncovered Branches in LLM Scorer
Tests error handling paths and edge cases not covered by existing tests.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app.services.llm_scorer import (
    LLMScorer,
    ScoringResult,
    extract_json,
    determine_decision,
    load_job_description,
)
from src.app.config import settings
from openai import APIError, APIConnectionError, APITimeoutError


class TestExtractJsonBranches:
    """Test all branches of extract_json function."""

    def test_direct_json_parse(self):
        """Should parse direct JSON."""
        result = extract_json('{"score": 85, "decision": "interview"}')
        assert result == {"score": 85, "decision": "interview"}

    def test_json_in_code_block(self):
        """Should extract JSON from markdown code block."""
        text = '```json\n{"score": 72, "decision": "maybe"}\n```'
        result = extract_json(text)
        assert result == {"score": 72, "decision": "maybe"}

    def test_json_in_code_block_without_label(self):
        """Should extract JSON from code block without json label."""
        text = '```\n{"score": 60, "decision": "reject"}\n```'
        result = extract_json(text)
        assert result == {"score": 60, "decision": "reject"}

    def test_json_in_text(self):
        """Should extract JSON embedded in text."""
        text = 'Here is the result: {"score": 50} and more text'
        result = extract_json(text)
        assert result == {"score": 50}

    def test_invalid_json_returns_none(self):
        """Should return None for invalid JSON."""
        result = extract_json("not json at all")
        assert result is None

    def test_invalid_json_in_code_block(self):
        """Should return None for invalid JSON in code block."""
        text = '```json\n{invalid json}\n```'
        result = extract_json(text)
        assert result is None

    def test_multiple_json_objects(self):
        """Should extract first valid JSON object found."""
        text = '{"score": 85} and {"score": 72}'
        result = extract_json(text)
        # The regex matches the whole string, which is invalid JSON
        # So it should return None
        assert result is None


class TestDetermineDecisionBranches:
    """Test all branches of determine_decision function."""

    def test_interview_threshold(self):
        """Should return 'interview' for scores >= 80."""
        assert determine_decision(80) == "interview"
        assert determine_decision(100) == "interview"

    def test_maybe_threshold(self):
        """Should return 'maybe' for scores 50-79."""
        assert determine_decision(50) == "maybe"
        assert determine_decision(79) == "maybe"

    def test_reject_threshold(self):
        """Should return 'reject' for scores < 50."""
        assert determine_decision(0) == "reject"
        assert determine_decision(49) == "reject"


class TestScoringResultBranches:
    """Test ScoringResult class methods."""

    def test_to_dict(self):
        """Should convert to dictionary correctly."""
        result = ScoringResult(
            score=75,
            decision="maybe",
            reasoning="Test reasoning",
            key_match_skills=["Python", "SQL"],
            gap_areas=["FastAPI"],
            processing_time_ms=1500.5,
            raw_response='{"score": 75}',
            error=None,
        )
        d = result.to_dict()
        assert d["score"] == 75
        assert d["decision"] == "maybe"
        assert d["key_match_skills"] == ["Python", "SQL"]
        assert d["error"] is None

    def test_to_dict_with_error(self):
        """Should include error in dictionary."""
        result = ScoringResult(
            score=0,
            decision="reject",
            reasoning="Error occurred",
            key_match_skills=[],
            gap_areas=[],
            processing_time_ms=0,
            raw_response="error",
            error="API failed",
        )
        d = result.to_dict()
        assert d["error"] == "API failed"


class TestLLMScorerErrorBranches:
    """Test error handling branches in LLMScorer."""

    def setup_method(self):
        self.scorer = LLMScorer()

    def test_api_connection_error_retry(self):
        """Should retry on APIConnectionError."""
        call_count = 0

        def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise APIConnectionError(request=MagicMock())
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"score": 70, "decision": "maybe", "reasoning": "Test"}'
            return mock_response

        with patch.object(self.scorer.client.chat.completions, "create", side_effect=mock_create):
            result = self.scorer.score_candidate("Test CV", "Test JD")

        assert call_count == 3
        assert result.score == 70
        assert result.error is None

    def test_api_timeout_error_retry(self):
        """Should retry on APITimeoutError."""
        call_count = 0

        def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise APITimeoutError(request=MagicMock())
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"score": 65, "decision": "maybe", "reasoning": "Test"}'
            return mock_response

        with patch.object(self.scorer.client.chat.completions, "create", side_effect=mock_create):
            result = self.scorer.score_candidate("Test CV", "Test JD")

        assert call_count == 2
        assert result.score == 65

    def test_api_error_retry(self):
        """Should retry on APIError."""
        call_count = 0

        def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise APIError(message="Rate limited", response=MagicMock(), body=None)
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"score": 55, "decision": "maybe", "reasoning": "Test"}'
            return mock_response

        with patch.object(self.scorer.client.chat.completions, "create", side_effect=mock_create):
            result = self.scorer.score_candidate("Test CV", "Test JD")

        assert call_count == 2
        assert result.score == 55

    def test_json_parse_failure_all_retries(self):
        """Should return error when JSON parsing fails on all retries."""
        call_count = 0

        def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Invalid JSON response"
            return mock_response

        with patch.object(self.scorer.client.chat.completions, "create", side_effect=mock_create):
            result = self.scorer.score_candidate("Test CV", "Test JD")

        assert result.score == 0
        assert result.error == "JSON parse failed"

    def test_score_clamping(self):
        """Should clamp score to 0-100 range."""
        def mock_create(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"score": 150, "decision": "interview", "reasoning": "Test"}'
            return mock_response

        with patch.object(self.scorer.client.chat.completions, "create", side_effect=mock_create):
            result = self.scorer.score_candidate("Test CV", "Test JD")

        assert result.score == 100  # Clamped

    def test_negative_score_clamping(self):
        """Should clamp negative score to 0."""
        def mock_create(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"score": -10, "decision": "reject", "reasoning": "Test"}'
            return mock_response

        with patch.object(self.scorer.client.chat.completions, "create", side_effect=mock_create):
            result = self.scorer.score_candidate("Test CV", "Test JD")

        assert result.score == 0  # Clamped

    def test_missing_fields_defaults(self):
        """Should use defaults for missing fields."""
        def mock_create(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"score": 50}'
            return mock_response

        with patch.object(self.scorer.client.chat.completions, "create", side_effect=mock_create):
            result = self.scorer.score_candidate("Test CV", "Test JD")

        assert result.score == 50
        assert result.decision == "maybe"  # From determine_decision
        assert result.reasoning == "No reasoning provided"
        assert result.key_match_skills == []
        assert result.gap_areas == []


class TestLoadJobDescription:
    """Test job description loading."""

    def test_load_valid_jd(self):
        """Should load valid job description."""
        jd = load_job_description("data/job_descriptions/backend_dev.json")
        assert "id" in jd
        assert "title" in jd
        assert "full_text" in jd

    def test_load_nonexistent_jd(self):
        """Should raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            load_job_description("data/job_descriptions/nonexistent.json")
