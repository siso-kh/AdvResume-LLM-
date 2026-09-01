"""
Test Checkpoint Manager
Verifies checkpoint saving, loading, and resume functionality.
"""
import json
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app.services.checkpoint_manager import CheckpointManager


class TestCheckpointManager:
    """Test suite for checkpoint manager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_dir = Path("data/benchmarks")
        self.test_dir.mkdir(parents=True, exist_ok=True)

    def _make_result(self, profile_id: str, job_id: str, score: int = 50) -> dict:
        """Create a mock result dictionary."""
        return {
            "profile_id": profile_id,
            "job_id": job_id,
            "archetype": "strong",
            "domain": "backend",
            "job_title": "Backend Dev",
            "score": score,
            "decision": "maybe",
            "reasoning": "Test",
            "key_match_skills": [],
            "gap_areas": [],
            "processing_time_ms": 1000,
            "is_adversarial": False,
            "attack_vector": None,
        }

    def test_add_and_flush(self, tmp_path):
        """Should add results and flush to disk."""
        checkpoint_path = tmp_path / "test_checkpoint.json"
        checkpoint = CheckpointManager(str(checkpoint_path), checkpoint_interval=2)

        # Add 2 results (should auto-flush)
        checkpoint.add(self._make_result("p1", "j1"))
        checkpoint.add(self._make_result("p2", "j2"))

        # File should exist
        assert checkpoint_path.exists()

        # Load and verify
        with open(checkpoint_path) as f:
            data = json.load(f)
        assert len(data) == 2

    def test_is_scored_detection(self, tmp_path):
        """Should detect already-scored combinations."""
        checkpoint_path = tmp_path / "test_checkpoint.json"
        checkpoint = CheckpointManager(str(checkpoint_path), checkpoint_interval=10)

        # Add a result
        checkpoint.add(self._make_result("p1", "j1"))
        checkpoint.flush()

        # Should detect it
        assert checkpoint.is_scored("p1", "j1") is True
        assert checkpoint.is_scored("p1", "j2") is False
        assert checkpoint.is_scored("p2", "j1") is False

    def test_resume_from_existing(self, tmp_path):
        """Should load existing checkpoint on init."""
        checkpoint_path = tmp_path / "test_checkpoint.json"

        # Create initial checkpoint
        checkpoint1 = CheckpointManager(str(checkpoint_path), checkpoint_interval=10)
        checkpoint1.add(self._make_result("p1", "j1"))
        checkpoint1.add(self._make_result("p2", "j2"))
        checkpoint1.flush()

        # Resume from existing
        checkpoint2 = CheckpointManager(str(checkpoint_path), checkpoint_interval=10)

        # Should have loaded existing results
        assert checkpoint2.is_scored("p1", "j1") is True
        assert checkpoint2.is_scored("p2", "j2") is True
        assert len(checkpoint2.existing_results) == 2

    def test_get_results(self, tmp_path):
        """Should return all results (existing + buffered)."""
        checkpoint_path = tmp_path / "test_checkpoint.json"
        checkpoint = CheckpointManager(str(checkpoint_path), checkpoint_interval=10)

        # Add existing
        checkpoint.add(self._make_result("p1", "j1"))
        checkpoint.flush()

        # Add more (buffered)
        checkpoint.add(self._make_result("p2", "j2"))
        checkpoint.add(self._make_result("p3", "j3"))

        results = checkpoint.get_results()
        assert len(results) == 3

    def test_atomic_write(self, tmp_path):
        """Should use atomic write (no .tmp files on success)."""
        checkpoint_path = tmp_path / "test_checkpoint.json"
        checkpoint = CheckpointManager(str(checkpoint_path), checkpoint_interval=10)

        checkpoint.add(self._make_result("p1", "j1"))
        checkpoint.flush()

        # No .tmp file should exist
        tmp_file = checkpoint_path.with_suffix(".tmp")
        assert not tmp_file.exists()

    def test_empty_flush_no_op(self, tmp_path):
        """Should not create file on empty flush."""
        checkpoint_path = tmp_path / "test_checkpoint.json"
        checkpoint = CheckpointManager(str(checkpoint_path), checkpoint_interval=10)

        checkpoint.flush()

        assert not checkpoint_path.exists()

    def test_get_summary(self, tmp_path):
        """Should return correct summary."""
        checkpoint_path = tmp_path / "test_checkpoint.json"
        checkpoint = CheckpointManager(str(checkpoint_path), checkpoint_interval=10)

        checkpoint.add(self._make_result("p1", "j1"))
        checkpoint.add(self._make_result("p2", "j2"))

        summary = checkpoint.get_summary()
        assert summary["total_results"] == 2
        assert summary["buffered_results"] == 2
        assert summary["scored_keys_count"] == 2
