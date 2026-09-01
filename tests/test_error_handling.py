"""
Test Per-Evaluation Error Handling
Verifies that the pipeline continues when individual evaluations fail.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app.services.llm_scorer import LLMScorer, load_job_description
from src.app.services.document_parser import DocumentParser
from src.app.config import settings


class TestErrorHandling:
    """Test suite for per-evaluation error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.scorer = LLMScorer()
        self.parser = DocumentParser()
        self.test_profiles = self._load_test_profiles()
        self.jd = load_job_description("data/job_descriptions/backend_dev.json")

    def _load_test_profiles(self):
        """Load a small set of test profiles."""
        with open(settings.PROFILES_PATH) as f:
            profiles = json.load(f)
        return [p for p in profiles if p["archetype"] in ["strong", "normal", "weak"]][:3]

    def test_pipeline_continues_after_error(self):
        """Pipeline should continue processing after one evaluation fails."""
        # Fail ALL retries for the 2nd evaluation
        call_count = 0

        def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if 2 <= call_count <= 4:  # Fail calls 2,3,4 (profile_0001's 3 retries)
                raise Exception("Simulated failure for eval #2")
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = (
                '{"score": 50, "decision": "maybe", "reasoning": "Test"}'
            )
            return mock_response

        results = []
        for profile in self.test_profiles:
            cv_text = self.parser.parse_pdf(f"{settings.CV_DIR}/{profile['id']}.pdf")
            with patch.object(self.scorer.client.chat.completions, "create", side_effect=mock_create):
                result = self.scorer.score_candidate(cv_text, self.jd["full_text"], self.jd.get("scoring_rubric"))
            results.append({"id": profile["id"], "score": result.score, "error": result.error})

        # All 3 profiles should have results (pipeline didn't crash)
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"

        # First and third should succeed
        assert results[0]["error"] is None, "Profile 0 should succeed"
        assert results[2]["error"] is None, "Profile 2 should succeed"

        # Second should have error
        assert results[1]["error"] is not None, "Profile 1 should have error"

    def test_error_result_has_zero_score(self):
        """Failed evaluations should return score=0."""
        def mock_create(*args, **kwargs):
            raise Exception("API failure")

        with open(settings.PROFILES_PATH) as f:
            profiles = json.load(f)
        profile = [p for p in profiles if p["archetype"] == "strong"][0]

        cv_text = self.parser.parse_pdf(f"{settings.CV_DIR}/{profile['id']}.pdf")
        with patch.object(self.scorer.client.chat.completions, "create", side_effect=mock_create):
            result = self.scorer.score_candidate(cv_text, self.jd["full_text"], self.jd.get("scoring_rubric"))

        assert result.score == 0
        assert result.decision == "reject"
        assert result.error is not None

    def test_successful_evaluations_not_affected(self):
        """Successful evaluations should work normally alongside failures."""
        call_count = 0

        def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Fail ALL retries for call #2 (calls 2, 3, 4)
            if 2 <= call_count <= 4:
                raise Exception("Fail all retries for eval #2")
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = (
                '{"score": 70, "decision": "maybe", "reasoning": "OK"}'
            )
            return mock_response

        results = []
        for profile in self.test_profiles:
            cv_text = self.parser.parse_pdf(f"{settings.CV_DIR}/{profile['id']}.pdf")
            with patch.object(self.scorer.client.chat.completions, "create", side_effect=mock_create):
                result = self.scorer.score_candidate(cv_text, self.jd["full_text"], self.jd.get("scoring_rubric"))
            results.append(result)

        # Profiles 0 and 2 should have score=70
        assert results[0].score == 70, f"Profile 0: expected 70, got {results[0].score}"
        assert results[2].score == 70, f"Profile 2: expected 70, got {results[2].score}"
        # Profile 1 should have score=0 (error)
        assert results[1].score == 0, f"Profile 1: expected 0, got {results[1].score}"
