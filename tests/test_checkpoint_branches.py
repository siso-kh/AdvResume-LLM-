"""
Tests for Uncovered Branches in Checkpoint Manager
Tests error handling, corrupt files, and edge cases.
"""
import json
import pytest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app.services.checkpoint_manager import CheckpointManager


class TestCheckpointCorruptFile:
    """Test handling of corrupt checkpoint files."""

    def test_corrupt_json_file(self, tmp_path):
        """Should handle corrupt JSON file gracefully."""
        checkpoint_path = tmp_path / "corrupt.json"
        checkpoint_path.write_text("not valid json {{{")

        # Should not raise, should start fresh
        checkpoint = CheckpointManager(str(checkpoint_path))
        assert checkpoint.existing_results == []
        assert checkpoint.scored_keys == set()

    def test_empty_file(self, tmp_path):
        """Should handle empty file gracefully."""
        checkpoint_path = tmp_path / "empty.json"
        checkpoint_path.write_text("")

        checkpoint = CheckpointManager(str(checkpoint_path))
        assert checkpoint.existing_results == []

    def test_wrong_structure_file(self, tmp_path):
        """Should handle file with wrong structure."""
        checkpoint_path = tmp_path / "wrong.json"
        # Create file with list of strings instead of list of dicts
        checkpoint_path.write_text('["invalid", "structure"]')

        checkpoint = CheckpointManager(str(checkpoint_path))
        # Should handle TypeError gracefully
        assert checkpoint.existing_results == []


class TestCheckpointAtomicWrite:
    """Test atomic write behavior."""

    def test_no_tmp_file_on_success(self, tmp_path):
        """Should not leave .tmp file on successful write."""
        checkpoint_path = tmp_path / "test.json"
        checkpoint = CheckpointManager(str(checkpoint_path), checkpoint_interval=1)

        checkpoint.add(self._make_result("p1", "j1"))
        checkpoint.flush()

        tmp_file = checkpoint_path.with_suffix(".tmp")
        assert not tmp_file.exists()
        assert checkpoint_path.exists()

    def _make_result(self, profile_id: str, job_id: str) -> dict:
        return {
            "profile_id": profile_id,
            "job_id": job_id,
            "archetype": "strong",
            "domain": "backend",
            "job_title": "Backend Dev",
            "score": 50,
            "decision": "maybe",
            "reasoning": "Test",
            "key_match_skills": [],
            "gap_areas": [],
            "processing_time_ms": 1000,
            "is_adversarial": False,
            "attack_vector": None,
        }


class TestCheckpointEdgeCases:
    """Test edge cases in checkpoint manager."""

    def test_flush_empty_buffer(self, tmp_path):
        """Should not create file when flushing empty buffer."""
        checkpoint_path = tmp_path / "test.json"
        checkpoint = CheckpointManager(str(checkpoint_path), checkpoint_interval=10)

        checkpoint.flush()
        assert not checkpoint_path.exists()

    def test_save_final_calls_flush(self, tmp_path):
        """Should call flush on save_final."""
        checkpoint_path = tmp_path / "test.json"
        checkpoint = CheckpointManager(str(checkpoint_path), checkpoint_interval=10)

        checkpoint.add(self._make_result("p1", "j1"))
        checkpoint.save_final()

        assert checkpoint_path.exists()
        with open(checkpoint_path) as f:
            data = json.load(f)
        assert len(data) == 1

    def test_print_summary(self, tmp_path, capsys):
        """Should print summary without errors."""
        checkpoint_path = tmp_path / "test.json"
        checkpoint = CheckpointManager(str(checkpoint_path), checkpoint_interval=10)

        checkpoint.add(self._make_result("p1", "j1"))
        checkpoint.print_summary()

        captured = capsys.readouterr()
        assert "CHECKPOINT SUMMARY" in captured.out
        assert "Total results:     1" in captured.out

    def test_multiple_flushes(self, tmp_path):
        """Should handle multiple flushes correctly."""
        checkpoint_path = tmp_path / "test.json"
        checkpoint = CheckpointManager(str(checkpoint_path), checkpoint_interval=10)

        # First flush
        checkpoint.add(self._make_result("p1", "j1"))
        checkpoint.flush()

        # Second flush (should append)
        checkpoint.add(self._make_result("p2", "j2"))
        checkpoint.flush()

        with open(checkpoint_path) as f:
            data = json.load(f)
        assert len(data) == 2

    def test_resume_preserves_existing(self, tmp_path):
        """Should preserve existing results on resume."""
        checkpoint_path = tmp_path / "test.json"

        # Create initial checkpoint
        checkpoint1 = CheckpointManager(str(checkpoint_path), checkpoint_interval=10)
        checkpoint1.add(self._make_result("p1", "j1"))
        checkpoint1.flush()

        # Resume and add more
        checkpoint2 = CheckpointManager(str(checkpoint_path), checkpoint_interval=10)
        checkpoint2.add(self._make_result("p2", "j2"))
        checkpoint2.flush()

        with open(checkpoint_path) as f:
            data = json.load(f)
        assert len(data) == 2
        assert data[0]["profile_id"] == "p1"
        assert data[1]["profile_id"] == "p2"

    def _make_result(self, profile_id: str, job_id: str) -> dict:
        return {
            "profile_id": profile_id,
            "job_id": job_id,
            "archetype": "strong",
            "domain": "backend",
            "job_title": "Backend Dev",
            "score": 50,
            "decision": "maybe",
            "reasoning": "Test",
            "key_match_skills": [],
            "gap_areas": [],
            "processing_time_ms": 1000,
            "is_adversarial": False,
            "attack_vector": None,
        }
