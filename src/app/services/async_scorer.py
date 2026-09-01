"""
Async Batch Scorer
Concurrent CV scoring with rate limiting and checkpointing.
"""
import asyncio
import json
import time
from typing import Optional
from dataclasses import dataclass

import httpx
from openai import AsyncOpenAI

from src.app.config import settings
from src.app.services.llm_scorer import extract_json, determine_decision
from src.app.services.rate_limiter import RateLimiter
from src.app.services.token_tracker import TokenTracker
from src.app.services.checkpoint_manager import CheckpointManager


@dataclass
class ScoringTask:
    """A single scoring task."""
    profile_id: str
    archetype: str
    domain: str
    job_id: str
    job_title: str
    cv_text: str
    job_description: str
    scoring_rubric: Optional[dict] = None


class AsyncScorer:
    """
    Async batch scorer for concurrent CV evaluation.

    Features:
    - Concurrent API calls with configurable parallelism
    - Rate limiting to prevent 429 errors
    - Token usage tracking
    - Checkpoint system for crash recovery
    """

    def __init__(
        self,
        max_concurrent: int = 4,
        requests_per_second: float = 2.0,
        model: Optional[str] = None,
    ):
        """
        Initialize async scorer.

        Args:
            max_concurrent: Maximum concurrent API calls
            requests_per_second: Rate limit (requests/second)
            model: Model to use (default from settings)
        """
        self.max_concurrent = max_concurrent
        self.model = model or settings.LLM_MODEL

        # Initialize components
        self.client = AsyncOpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
        )
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.rate_limiter = RateLimiter(
            requests_per_second=requests_per_second,
            burst_size=max_concurrent,
        )
        self.token_tracker = TokenTracker()

        # Stats
        self.completed = 0
        self.failed = 0
        self.start_time = None

    def _build_system_prompt(self, job_description: str, scoring_rubric: dict) -> str:
        """Build the system prompt with rubric and JD."""
        rubric_text = self._format_rubric(scoring_rubric)

        return f"""You are an expert technical recruiter with 15 years of experience. Score the following CV against the job description using the provided rubric.

SCORING RUBRIC:
{rubric_text}

RULES:
1. Be strict and objective. Do not inflate scores.
2. Each category is scored independently based on evidence in the CV.
3. If the CV does not mention a skill, do NOT assume the candidate has it.
4. "Nice to have" skills get bonus points only within the technical skills category.
5. Experience quality matters more than just years.
6. Your reasoning must reference specific evidence from the CV.

JOB DESCRIPTION:
{job_description}

OUTPUT FORMAT (JSON only, no other text):
{{
  "score": <0-100>,
  "decision": "interview" | "maybe" | "reject",
  "reasoning": "<1-2 sentences citing specific CV evidence>",
  "key_match_skills": ["<skill from CV that matches JD>", ...],
  "gap_areas": ["<requirement from JD not found in CV>", ...]
}}"""

    def _format_rubric(self, rubric: dict) -> str:
        """Format scoring rubric for the prompt."""
        lines = []
        for category, details in rubric.items():
            max_pts = details.get("max_points", "?")
            desc = details.get("description", "")
            lines.append(f"- {category.replace('_', ' ').title()} (0-{max_pts} points): {desc}")
        return "\n".join(lines)

    async def _score_single(self, task: ScoringTask) -> dict:
        """Score a single CV against a job description."""
        # Default rubric if not provided
        rubric = task.scoring_rubric or {
            "technical_skills_match": {"max_points": 30, "description": "Does the candidate have the required technical skills?"},
            "experience_level": {"max_points": 25, "description": "Does the years and quality of experience match requirements?"},
            "education_relevance": {"max_points": 20, "description": "Is the education background relevant?"},
            "additional_strengths": {"max_points": 15, "description": "Certifications, languages, side projects."},
            "overall_fit": {"max_points": 10, "description": "Holistic assessment."},
        }

        system_prompt = self._build_system_prompt(task.job_description, rubric)

        # Acquire rate limit token
        await self.rate_limiter.acquire()

        start_time = time.perf_counter()
        try:
            async with self.semaphore:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"CANDIDATE CV:\n\n{task.cv_text}"},
                    ],
                    temperature=settings.TEMPERATURE,
                    max_tokens=settings.MAX_TOKENS,
                )

            # Track tokens
            self.token_tracker.record(response, self.model)

            raw_content = response.choices[0].message.content
            processing_time = (time.perf_counter() - start_time) * 1000

            # Parse JSON response
            parsed = extract_json(raw_content)
            if parsed is None:
                return self._error_result(task, "JSON parse failed", processing_time, raw_content)

            # Extract fields with defaults
            score = max(0, min(100, parsed.get("score", 0)))
            decision = parsed.get("decision", determine_decision(score))

            return {
                "profile_id": task.profile_id,
                "archetype": task.archetype,
                "domain": task.domain,
                "job_id": task.job_id,
                "job_title": task.job_title,
                "score": score,
                "decision": decision,
                "reasoning": parsed.get("reasoning", "No reasoning provided"),
                "key_match_skills": parsed.get("key_match_skills", []),
                "gap_areas": parsed.get("gap_areas", []),
                "processing_time_ms": processing_time,
                "is_adversarial": False,
                "attack_vector": None,
                "error": None,
            }

        except Exception as e:
            processing_time = (time.perf_counter() - start_time) * 1000
            return self._error_result(task, str(e), processing_time)

    def _error_result(self, task: ScoringTask, error: str, processing_time: float, raw_response: str = "") -> dict:
        """Create an error result dictionary."""
        return {
            "profile_id": task.profile_id,
            "archetype": task.archetype,
            "domain": task.domain,
            "job_id": task.job_id,
            "job_title": task.job_title,
            "score": 0,
            "decision": "reject",
            "reasoning": f"Error: {error}",
            "key_match_skills": [],
            "gap_areas": [],
            "processing_time_ms": processing_time,
            "is_adversarial": False,
            "attack_vector": None,
            "error": error,
        }

    async def score_batch(
        self,
        tasks: list[ScoringTask],
        checkpoint: Optional[CheckpointManager] = None,
        progress_callback=None,
    ) -> list[dict]:
        """
        Score a batch of CVs concurrently.

        Args:
            tasks: List of ScoringTask objects
            checkpoint: Optional checkpoint manager for saving progress
            progress_callback: Optional callback for progress updates

        Returns:
            List of result dictionaries
        """
        self.start_time = time.perf_counter()
        self.completed = 0
        self.failed = 0

        print(f"\nStarting async batch scoring ({len(tasks)} tasks, {self.max_concurrent} concurrent)")

        async def score_with_progress(task: ScoringTask) -> dict:
            result = await self._score_single(task)
            self.completed += 1

            if result["error"]:
                self.failed += 1

            # Checkpoint if provided
            if checkpoint:
                checkpoint.add(result)

            # Progress callback
            if progress_callback:
                progress_callback(self.completed, len(tasks), result)

            return result

        # Run all tasks concurrently
        results = await asyncio.gather(*[score_with_progress(task) for task in tasks])

        # Final checkpoint save
        if checkpoint:
            checkpoint.save_final()

        return list(results)

    def print_summary(self):
        """Print scoring summary."""
        elapsed = time.perf_counter() - self.start_time if self.start_time else 0
        print("\n" + "=" * 50)
        print("  ASYNC SCORING SUMMARY")
        print("=" * 50)
        print(f"  Completed:    {self.completed}")
        print(f"  Failed:       {self.failed}")
        print(f"  Success rate: {((self.completed - self.failed) / max(self.completed, 1)) * 100:.1f}%")
        print(f"  Total time:   {elapsed:.1f}s")
        print(f"  Avg per eval: {elapsed / max(self.completed, 1):.1f}s")
        print(f"  Throughput:   {self.completed / max(elapsed, 1):.2f} evals/s")
        print("=" * 50)

        # Token usage
        self.token_tracker.print_summary()
