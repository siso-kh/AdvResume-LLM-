"""
Unit Tests for Async Scorer
Tests async scoring logic with mocks (no real API calls).
"""
import asyncio
import json
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app.services.async_scorer import AsyncScorer, ScoringTask
from src.app.services.checkpoint_manager import CheckpointManager
from src.app.config import settings


def make_task(profile_id: str = "test_001", archetype: str = "strong") -> ScoringTask:
    """Create a test task."""
    return ScoringTask(
        profile_id=profile_id,
        archetype=archetype,
        domain="backend",
        job_id="jd_backend_dev",
        job_title="Backend Developer",
        cv_text="Test CV content with Python, FastAPI, PostgreSQL experience.",
        job_description="Looking for a backend developer with Python skills.",
        scoring_rubric={
            "technical_skills": {"max_points": 30, "description": "Technical skills match"},
            "experience": {"max_points": 25, "description": "Experience level"},
        },
    )


def mock_response(score: int = 75, decision: str = "maybe") -> MagicMock:
    """Create a mock API response."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = json.dumps({
        "score": score,
        "decision": decision,
        "reasoning": "Test reasoning",
        "key_match_skills": ["Python"],
        "gap_areas": ["FastAPI"],
    })
    response.usage = MagicMock()
    response.usage.prompt_tokens = 1000
    response.usage.completion_tokens = 500
    return response


class TestAsyncScorerInit:
    """Test async scorer initialization."""

    def test_init_default(self):
        """Should initialize with default settings."""
        scorer = AsyncScorer()
        assert scorer.max_concurrent == 4
        assert scorer.model == settings.LLM_MODEL

    def test_init_custom(self):
        """Should initialize with custom settings."""
        scorer = AsyncScorer(max_concurrent=8, requests_per_second=5.0, model="test-model")
        assert scorer.max_concurrent == 8
        assert scorer.model == "test-model"


class TestBuildSystemPrompt:
    """Test system prompt building."""

    def test_build_prompt(self):
        """Should build prompt with rubric and JD."""
        scorer = AsyncScorer()
        rubric = {
            "technical_skills": {"max_points": 30, "description": "Skills match"},
        }
        prompt = scorer._build_system_prompt("Job description text", rubric)

        assert "SCORING RUBRIC" in prompt
        assert "Job description text" in prompt
        assert "Technical Skills" in prompt  # Formatted with title case

    def test_format_rubric(self):
        """Should format rubric correctly."""
        scorer = AsyncScorer()
        rubric = {
            "technical_skills": {"max_points": 30, "description": "Skills"},
            "experience": {"max_points": 25, "description": "Experience"},
        }
        formatted = scorer._format_rubric(rubric)

        assert "0-30 points" in formatted
        assert "0-25 points" in formatted
        assert "Technical Skills" in formatted


class TestScoreSingle:
    """Test single CV scoring."""

    @pytest.mark.asyncio
    async def test_score_single_success(self):
        """Should score a single CV successfully."""
        scorer = AsyncScorer(max_concurrent=1, requests_per_second=100.0)

        with patch.object(scorer.client.chat.completions, "create", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response(85, "interview")
            result = await scorer._score_single(make_task())

        assert result["score"] == 85
        assert result["decision"] == "interview"
        assert result["error"] is None
        assert result["profile_id"] == "test_001"

    @pytest.mark.asyncio
    async def test_score_single_json_parse_failure(self):
        """Should handle JSON parse failure."""
        scorer = AsyncScorer(max_concurrent=1, requests_per_second=100.0)

        with patch.object(scorer.client.chat.completions, "create", new_callable=AsyncMock) as mock:
            response = MagicMock()
            response.choices = [MagicMock()]
            response.choices[0].message.content = "Invalid JSON response"
            response.usage = MagicMock()
            response.usage.prompt_tokens = 100
            response.usage.completion_tokens = 50
            mock.return_value = response

            result = await scorer._score_single(make_task())

        assert result["score"] == 0
        assert result["error"] == "JSON parse failed"

    @pytest.mark.asyncio
    async def test_score_single_api_error(self):
        """Should handle API errors."""
        scorer = AsyncScorer(max_concurrent=1, requests_per_second=100.0)

        with patch.object(scorer.client.chat.completions, "create", new_callable=AsyncMock) as mock:
            mock.side_effect = Exception("API error")

            result = await scorer._score_single(make_task())

        assert result["score"] == 0
        assert result["error"] == "API error"

    @pytest.mark.asyncio
    async def test_score_single_clamps_score(self):
        """Should clamp score to 0-100."""
        scorer = AsyncScorer(max_concurrent=1, requests_per_second=100.0)

        with patch.object(scorer.client.chat.completions, "create", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response(150, "interview")
            result = await scorer._score_single(make_task())

        assert result["score"] == 100  # Clamped


class TestScoreBatch:
    """Test batch scoring."""

    @pytest.mark.asyncio
    async def test_score_batch_multiple(self):
        """Should score multiple CVs."""
        scorer = AsyncScorer(max_concurrent=2, requests_per_second=100.0)

        tasks = [make_task(f"test_{i}") for i in range(3)]

        with patch.object(scorer.client.chat.completions, "create", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response(70, "maybe")
            results = await scorer.score_batch(tasks)

        assert len(results) == 3
        for r in results:
            assert r["score"] == 70
            assert r["error"] is None

    @pytest.mark.asyncio
    async def test_score_batch_with_checkpoint(self, tmp_path):
        """Should save results to checkpoint."""
        scorer = AsyncScorer(max_concurrent=1, requests_per_second=100.0)
        checkpoint = CheckpointManager(str(tmp_path / "test.json"), checkpoint_interval=1)

        tasks = [make_task("test_001"), make_task("test_002")]

        with patch.object(scorer.client.chat.completions, "create", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response(65, "maybe")
            results = await scorer.score_batch(tasks, checkpoint=checkpoint)

        # Checkpoint should have results
        checkpoint_results = checkpoint.get_results()
        assert len(checkpoint_results) == 2

    @pytest.mark.asyncio
    async def test_score_batch_progress_callback(self):
        """Should call progress callback."""
        scorer = AsyncScorer(max_concurrent=1, requests_per_second=100.0)
        callback_results = []

        def callback(completed, total, result):
            callback_results.append({"completed": completed, "total": total})

        tasks = [make_task("test_001"), make_task("test_002")]

        with patch.object(scorer.client.chat.completions, "create", new_callable=AsyncMock) as mock:
            mock.return_value = mock_response(75, "maybe")
            await scorer.score_batch(tasks, progress_callback=callback)

        assert len(callback_results) == 2
        assert callback_results[0]["completed"] == 1
        assert callback_results[1]["completed"] == 2

    @pytest.mark.asyncio
    async def test_score_batch_tracks_errors(self):
        """Should track failed evaluations."""
        scorer = AsyncScorer(max_concurrent=1, requests_per_second=100.0)

        call_count = 0
        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("Simulated failure")
            return mock_response(70, "maybe")

        with patch.object(scorer.client.chat.completions, "create", side_effect=mock_create):
            results = await scorer.score_batch([make_task("t1"), make_task("t2"), make_task("t3")])

        assert scorer.completed == 3
        assert scorer.failed == 1


class TestErrorResult:
    """Test error result creation."""

    def test_error_result(self):
        """Should create proper error result."""
        scorer = AsyncScorer()
        task = make_task()
        result = scorer._error_result(task, "Test error", 100.0, "raw")

        assert result["score"] == 0
        assert result["decision"] == "reject"
        assert result["error"] == "Test error"
        assert result["processing_time_ms"] == 100.0


class TestScoringTask:
    """Test ScoringTask dataclass."""

    def test_scoring_task_creation(self):
        """Should create task with all fields."""
        task = ScoringTask(
            profile_id="p1",
            archetype="strong",
            domain="backend",
            job_id="j1",
            job_title="Dev",
            cv_text="CV",
            job_description="JD",
        )
        assert task.profile_id == "p1"
        assert task.archetype == "strong"
        assert task.scoring_rubric is None  # Optional


class TestPrintSummary:
    """Test print_summary method."""

    def test_print_summary(self, capsys):
        """Should print summary without errors."""
        scorer = AsyncScorer()
        scorer.completed = 10
        scorer.failed = 2
        scorer.start_time = __import__('time').perf_counter() - 10  # 10 seconds ago

        scorer.print_summary()

        captured = capsys.readouterr()
        assert "ASYNC SCORING SUMMARY" in captured.out
        assert "Completed:" in captured.out
        assert "Failed:" in captured.out
