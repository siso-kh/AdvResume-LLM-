"""
Checkpoint Manager
Provides crash recovery and resume capability for long-running evaluations.
"""
import json
import time
from pathlib import Path
from typing import Optional


class CheckpointManager:
    """
    Manages checkpoints for evaluation results.

    Saves progress periodically to allow resuming after crashes.
    Uses atomic writes (temp file + rename) to prevent corruption.
    """

    def __init__(
        self,
        checkpoint_path: str,
        checkpoint_interval: int = 10,
    ):
        """
        Initialize checkpoint manager.

        Args:
            checkpoint_path: Path to checkpoint JSON file
            checkpoint_interval: Save every N evaluations
        """
        self.path = Path(checkpoint_path)
        self.interval = checkpoint_interval
        self.buffer: list[dict] = []
        self.total_count = 0
        self.buffer_count = 0

        # Load existing checkpoint if resuming
        self.existing_results = self._load_checkpoint()
        self.scored_keys = self._build_scored_keys()

    def _load_checkpoint(self) -> list[dict]:
        """Load existing checkpoint file."""
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                print(f"  Loaded {len(data)} existing results from checkpoint")
                return data
            except (json.JSONDecodeError, KeyError):
                print("  WARNING: Corrupt checkpoint file, starting fresh")
                return []
        return []

    def _build_scored_keys(self) -> set:
        """Build set of already-scored (profile_id, job_id) combinations."""
        return {(r["profile_id"], r["job_id"]) for r in self.existing_results}

    def is_scored(self, profile_id: str, job_id: str) -> bool:
        """Check if a profile+job combination has already been scored."""
        return (profile_id, job_id) in self.scored_keys

    def add(self, result: dict):
        """
        Add a result to the checkpoint buffer.

        Args:
            result: Evaluation result dictionary
        """
        self.buffer.append(result)
        self.buffer_count += 1
        self.total_count += 1

        # Flush if interval reached
        if self.buffer_count >= self.interval:
            self.flush()

    def flush(self):
        """Flush buffer to disk with atomic write."""
        if not self.buffer:
            return

        # Merge existing + new results
        all_results = self.existing_results + self.buffer

        # Atomic write: temp file → rename
        temp_path = self.path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False)

            # Atomic rename (works on most OS)
            temp_path.replace(self.path)

            # Update state
            self.existing_results = all_results
            self.scored_keys = {(r["profile_id"], r["job_id"]) for r in all_results}
            self.buffer = []
            self.buffer_count = 0

        except Exception as e:
            # Clean up temp file on failure
            if temp_path.exists():
                temp_path.unlink()
            raise e

    def save_final(self):
        """Save final results (called at end of run)."""
        self.flush()

    def get_results(self) -> list[dict]:
        """Get all results (existing + buffered)."""
        return self.existing_results + self.buffer

    def get_summary(self) -> dict:
        """Get checkpoint summary."""
        # Include buffered results in scored keys count
        all_scored = self.scored_keys.copy()
        for r in self.buffer:
            all_scored.add((r["profile_id"], r["job_id"]))
        
        return {
            "checkpoint_path": str(self.path),
            "total_results": len(self.existing_results) + len(self.buffer),
            "buffered_results": len(self.buffer),
            "scored_keys_count": len(all_scored),
            "checkpoint_exists": self.path.exists(),
        }

    def print_summary(self):
        """Print formatted checkpoint summary."""
        summary = self.get_summary()
        print("\n" + "=" * 50)
        print("  CHECKPOINT SUMMARY")
        print("=" * 50)
        print(f"  Checkpoint file:   {summary['checkpoint_path']}")
        print(f"  Total results:     {summary['total_results']}")
        print(f"  Buffered (unsaved):{summary['buffered_results']}")
        print(f"  Scored pairs:      {summary['scored_keys_count']}")
        print(f"  File exists:       {summary['checkpoint_exists']}")
        print("=" * 50)
