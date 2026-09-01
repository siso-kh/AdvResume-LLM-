"""
Token Usage Tracking
Monitors API consumption and provides budget management.
"""
import json
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class TokenUsage:
    """Single request token usage."""
    timestamp: float
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float


class TokenTracker:
    """Tracks token usage across API calls."""

    # Cost per 1M tokens (USD) - update as needed
    MODEL_COSTS = {
        "mistral-large": {"prompt": 2.0, "completion": 6.0},
        "mistral-medium-3-5": {"prompt": 0.27, "completion": 1.1},
        "deepseek-v4-flash": {"prompt": 0.0, "completion": 0.0},  # Free
        "qwen3.8-27b": {"prompt": 0.0, "completion": 0.0},  # Free
        # Default for unknown models
        "default": {"prompt": 1.0, "completion": 3.0},
    }

    def __init__(self, daily_budget: int = 7_000_000):
        """
        Initialize token tracker.

        Args:
            daily_budget: Daily token budget (default 7M)
        """
        self.daily_budget = daily_budget
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_cost = 0.0
        self.history: list[TokenUsage] = []
        self.start_time = time.time()

    def record(self, response, model: str) -> TokenUsage:
        """
        Record token usage from an API response.

        Args:
            response: OpenAI API response object
            model: Model name used

        Returns:
            TokenUsage object with recorded data
        """
        usage = response.usage
        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens
        total_tokens = prompt_tokens + completion_tokens

        # Calculate cost
        cost = self._calculate_cost(model, prompt_tokens, completion_tokens)

        # Update totals
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_cost += cost

        # Create usage record
        record = TokenUsage(
            timestamp=time.time(),
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
        )
        self.history.append(record)

        return record

    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost for a single request."""
        costs = self.MODEL_COSTS.get(model, self.MODEL_COSTS["default"])
        prompt_cost = (prompt_tokens / 1_000_000) * costs["prompt"]
        completion_cost = (completion_tokens / 1_000_000) * costs["completion"]
        return prompt_cost + completion_cost

    def get_summary(self) -> dict:
        """Get usage summary."""
        return {
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
            "total_cost_usd": round(self.total_cost, 4),
            "budget_remaining": self.daily_budget - self.total_prompt_tokens,
            "budget_used_percent": round(
                (self.total_prompt_tokens / self.daily_budget) * 100, 2
            ),
            "requests_count": len(self.history),
            "elapsed_seconds": round(time.time() - self.start_time, 2),
        }

    def check_budget(self) -> tuple[bool, str]:
        """
        Check if within budget limits.

        Returns:
            Tuple of (is_within_budget, message)
        """
        summary = self.get_summary()
        used_percent = summary["budget_used_percent"]

        if used_percent >= 95:
            return False, f"CRITICAL: {used_percent}% of budget used ({summary['budget_remaining']:,} tokens remaining)"
        elif used_percent >= 80:
            return True, f"WARNING: {used_percent}% of budget used ({summary['budget_remaining']:,} tokens remaining)"
        else:
            return True, f"OK: {used_percent}% of budget used ({summary['budget_remaining']:,} tokens remaining)"

    def save(self, path: str):
        """Save usage history to JSON file."""
        data = {
            "summary": self.get_summary(),
            "history": [asdict(h) for h in self.history],
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def print_summary(self):
        """Print formatted usage summary."""
        summary = self.get_summary()
        print("\n" + "=" * 50)
        print("  TOKEN USAGE SUMMARY")
        print("=" * 50)
        print(f"  Prompt tokens:     {summary['total_prompt_tokens']:>12,}")
        print(f"  Completion tokens: {summary['total_completion_tokens']:>12,}")
        print(f"  Total tokens:      {summary['total_tokens']:>12,}")
        print(f"  Total cost:        ${summary['total_cost_usd']:>11.4f}")
        print(f"  Budget used:       {summary['budget_used_percent']:>11.2f}%")
        print(f"  Budget remaining:  {summary['budget_remaining']:>12,}")
        print(f"  Requests:          {summary['requests_count']:>12}")
        print(f"  Elapsed:           {summary['elapsed_seconds']:>11.1f}s")
        print("=" * 50)
