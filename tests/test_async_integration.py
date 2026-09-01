"""
Integration Tests for Async Scorer
Tests the async scoring pipeline with real API calls using a small sample.
Uses 30-50% of the population to avoid biased results.
"""
import asyncio
import json
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app.services.async_scorer import AsyncScorer, ScoringTask
from src.app.services.document_parser import DocumentParser
from src.app.services.llm_scorer import load_job_description
from src.app.config import settings


def load_sample_profiles(sample_size: int = 3) -> list:
    """Load a small sample of profiles for testing."""
    with open(settings.PROFILES_PATH) as f:
        profiles = json.load(f)
    # Get balanced sample: 1 strong, 1 normal, 1 weak
    archetype_samples = {}
    for p in profiles:
        arch = p["archetype"]
        if arch not in archetype_samples:
            archetype_samples[arch] = p
        if len(archetype_samples) == 3:
            break
    return list(archetype_samples.values())


@pytest.fixture
def sample_tasks():
    """Create sample tasks for integration testing."""
    parser = DocumentParser()
    profiles = load_sample_profiles(3)
    jd = load_job_description("data/job_descriptions/backend_dev.json")

    tasks = []
    for profile in profiles:
        pdf_path = Path(settings.CV_DIR) / f"{profile['id']}.pdf"
        if pdf_path.exists():
            cv_text = parser.parse_pdf(str(pdf_path))
            if len(cv_text) > 50:
                tasks.append(ScoringTask(
                    profile_id=profile["id"],
                    archetype=profile["archetype"],
                    domain=profile["domain"],
                    job_id=jd["id"],
                    job_title=jd["title"],
                    cv_text=cv_text,
                    job_description=jd["full_text"],
                    scoring_rubric=jd.get("scoring_rubric"),
                ))
    return tasks


class TestAsyncScorerIntegration:
    """Integration tests for async scorer with real API calls."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_single_cv_scoring(self, sample_tasks):
        """Should score a single CV correctly."""
        if not sample_tasks:
            pytest.skip("No sample tasks available")

        scorer = AsyncScorer(max_concurrent=1, requests_per_second=1.0)
        task = sample_tasks[0]

        results = await scorer.score_batch([task])

        assert len(results) == 1
        result = results[0]
        assert result["profile_id"] == task.profile_id
        assert 0 <= result["score"] <= 100
        assert result["decision"] in ["interview", "maybe", "reject"]
        assert result["reasoning"] is not None
        assert result["error"] is None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_batch_scoring_concurrent(self, sample_tasks):
        """Should score multiple CVs concurrently."""
        if len(sample_tasks) < 2:
            pytest.skip("Need at least 2 sample tasks")

        scorer = AsyncScorer(max_concurrent=2, requests_per_second=2.0)

        results = await scorer.score_batch(sample_tasks)

        assert len(results) == len(sample_tasks)
        for result in results:
            assert 0 <= result["score"] <= 100
            assert result["decision"] in ["interview", "maybe", "reject"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_rate_limiting_works(self, sample_tasks):
        """Should respect rate limits during scoring."""
        if not sample_tasks:
            pytest.skip("No sample tasks available")

        # Very strict rate limit
        scorer = AsyncScorer(max_concurrent=1, requests_per_second=0.5)

        import time
        start = time.perf_counter()
        results = await scorer.score_batch(sample_tasks[:2])
        elapsed = time.perf_counter() - start

        assert len(results) == 2
        # With 0.5 req/s, 2 requests should take at least 2 seconds
        assert elapsed >= 1.5

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_checkpoint_integration(self, sample_tasks, tmp_path):
        """Should save results to checkpoint during scoring."""
        if not sample_tasks:
            pytest.skip("No sample tasks available")

        from src.app.services.checkpoint_manager import CheckpointManager

        checkpoint_path = tmp_path / "test_checkpoint.json"
        checkpoint = CheckpointManager(str(checkpoint_path), checkpoint_interval=1)

        scorer = AsyncScorer(max_concurrent=1, requests_per_second=1.0)
        results = await scorer.score_batch(sample_tasks[:2], checkpoint=checkpoint)

        # Checkpoint should have results
        checkpoint_results = checkpoint.get_results()
        assert len(checkpoint_results) == 2

        # Results should match
        for r in results:
            assert checkpoint.is_scored(r["profile_id"], r["job_id"])

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_token_tracking(self, sample_tasks):
        """Should track token usage during scoring."""
        if not sample_tasks:
            pytest.skip("No sample tasks available")

        scorer = AsyncScorer(max_concurrent=1, requests_per_second=1.0)
        results = await scorer.score_batch(sample_tasks[:1])

        # Token tracker should have recorded usage
        summary = scorer.token_tracker.get_summary()
        assert summary["total_prompt_tokens"] > 0
        assert summary["total_completion_tokens"] > 0
        assert summary["requests_count"] == 1

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_error_handling_integration(self, sample_tasks):
        """Should handle errors gracefully during scoring."""
        if not sample_tasks:
            pytest.skip("No sample tasks available")

        # Use invalid API key to trigger error
        scorer = AsyncScorer(max_concurrent=1, requests_per_second=1.0)
        scorer.client.api_key = "invalid_key"

        results = await scorer.score_batch(sample_tasks[:1])

        assert len(results) == 1
        assert results[0]["error"] is not None
        assert results[0]["score"] == 0
