"""
LLM Scoring Service
Evaluates CVs against job descriptions using rubric-anchored scoring.
"""
import json
import time
import re
import logging
from typing import Optional
from openai import OpenAI, APIError, APIConnectionError, APITimeoutError
from src.app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScoringResult:
    """Structured scoring result."""

    def __init__(
        self,
        score: int,
        decision: str,
        reasoning: str,
        key_match_skills: list[str],
        gap_areas: list[str],
        processing_time_ms: float,
        raw_response: str,
        error: Optional[str] = None,
    ):
        self.score = score
        self.decision = decision
        self.reasoning = reasoning
        self.key_match_skills = key_match_skills
        self.gap_areas = gap_areas
        self.processing_time_ms = processing_time_ms
        self.raw_response = raw_response
        self.error = error

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "decision": self.decision,
            "reasoning": self.reasoning,
            "key_match_skills": self.key_match_skills,
            "gap_areas": self.gap_areas,
            "processing_time_ms": self.processing_time_ms,
            "raw_response": self.raw_response,
            "error": self.error,
        }


def extract_json(text: str) -> Optional[dict]:
    """Extract JSON from LLM response, handling markdown code blocks."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from code block
    match = re.search(r'```(?:json)?\s*(.*?)```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding JSON object
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def determine_decision(score: int) -> str:
    """Map score to decision based on thresholds."""
    if score >= settings.SCORE_INTERVIEW_THRESHOLD:
        return "interview"
    elif score >= settings.SCORE_MAYBE_THRESHOLD:
        return "maybe"
    else:
        return "reject"


class LLMScorer:
    """Scores CVs against job descriptions using LLM."""

    def __init__(self, model: Optional[str] = None, base_url: Optional[str] = None, api_key: Optional[str] = None):
        """Initialize scorer with optional model override."""
        self.client = OpenAI(
            base_url=base_url or settings.LLM_BASE_URL,
            api_key=api_key or settings.LLM_API_KEY,
        )
        self.model = model or settings.LLM_MODEL

    def build_system_prompt(self, job_description: str, scoring_rubric: dict) -> str:
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

    def score_candidate(
        self,
        cv_text: str,
        job_description: str,
        scoring_rubric: Optional[dict] = None,
    ) -> ScoringResult:
        """Score a CV against a job description with retry logic."""
        # Default rubric if not provided
        if scoring_rubric is None:
            scoring_rubric = {
                "technical_skills_match": {"max_points": 30, "description": "Does the candidate have the required technical skills?"},
                "experience_level": {"max_points": 25, "description": "Does the years and quality of experience match requirements?"},
                "education_relevance": {"max_points": 20, "description": "Is the education background relevant?"},
                "additional_strengths": {"max_points": 15, "description": "Certifications, languages, side projects."},
                "overall_fit": {"max_points": 10, "description": "Holistic assessment."},
            }

        system_prompt = self.build_system_prompt(job_description, scoring_rubric)
        
        # Retry logic with exponential backoff
        last_exception = None
        for attempt in range(settings.MAX_RETRIES):
            start_time = time.perf_counter()  # Use perf_counter for precise timing
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"CANDIDATE CV:\n\n{cv_text}"},
                    ],
                    temperature=settings.TEMPERATURE,
                    max_tokens=settings.MAX_TOKENS,
                )
                raw_content = response.choices[0].message.content
                processing_time = (time.perf_counter() - start_time) * 1000

                # Parse JSON response
                parsed = extract_json(raw_content)
                if parsed is None:
                    logger.warning(f"JSON parse failed on attempt {attempt + 1}")
                    if attempt < settings.MAX_RETRIES - 1:
                        time.sleep(settings.RETRY_BACKOFF ** attempt)
                        continue
                    return ScoringResult(
                        score=0,
                        decision="reject",
                        reasoning=f"Failed to parse LLM response after {settings.MAX_RETRIES} attempts",
                        key_match_skills=[],
                        gap_areas=[],
                        processing_time_ms=processing_time,
                        raw_response=raw_content,
                        error="JSON parse failed",
                    )

                # Extract fields with defaults
                score = max(0, min(100, parsed.get("score", 0)))
                decision = parsed.get("decision", determine_decision(score))
                reasoning = parsed.get("reasoning", "No reasoning provided")
                key_match_skills = parsed.get("key_match_skills", [])
                gap_areas = parsed.get("gap_areas", [])

                return ScoringResult(
                    score=score,
                    decision=decision,
                    reasoning=reasoning,
                    key_match_skills=key_match_skills,
                    gap_areas=gap_areas,
                    processing_time_ms=processing_time,
                    raw_response=raw_content,
                )

            except (APIConnectionError, APITimeoutError) as e:
                last_exception = e
                processing_time = (time.perf_counter() - start_time) * 1000
                logger.warning(f"API connection/timeout error on attempt {attempt + 1}: {e}")
                if attempt < settings.MAX_RETRIES - 1:
                    time.sleep(settings.RETRY_BACKOFF ** attempt)
                    continue
            except APIError as e:
                last_exception = e
                processing_time = (time.perf_counter() - start_time) * 1000
                logger.error(f"API error on attempt {attempt + 1}: {e}")
                if attempt < settings.MAX_RETRIES - 1:
                    time.sleep(settings.RETRY_BACKOFF ** attempt)
                    continue
            except Exception as e:
                last_exception = e
                processing_time = (time.perf_counter() - start_time) * 1000
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt < settings.MAX_RETRIES - 1:
                    time.sleep(settings.RETRY_BACKOFF ** attempt)
                    continue
        
        # All retries failed
        return ScoringResult(
            score=0,
            decision="reject",
            reasoning=f"Error after {settings.MAX_RETRIES} attempts: {str(last_exception)}",
            key_match_skills=[],
            gap_areas=[],
            processing_time_ms=0,
            raw_response=str(last_exception),
            error=str(last_exception),
        )


def load_job_description(jd_path: str) -> dict:
    """Load a job description from JSON file."""
    with open(jd_path, "r", encoding="utf-8") as f:
        return json.load(f)
