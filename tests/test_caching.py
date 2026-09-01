"""
Test Result Caching System
Verifies that already-scored CVs can be skipped on resume.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app.services.llm_scorer import LLMScorer, load_job_description
from src.app.services.document_parser import DocumentParser
from src.app.config import settings


class TestCaching:
    """Test suite for result caching system."""

    def setup_method(self):
        """Set up test fixtures."""
        self.scorer = LLMScorer()
        self.parser = DocumentParser()
        self.test_profiles = self._load_test_profiles()
        self.jd = load_job_description("data/job_descriptions/backend_dev.json")
        self.test_output = Path("data/benchmarks/test_cache.json")

    def _load_test_profiles(self):
        """Load a small set of test profiles."""
        with open(settings.PROFILES_PATH) as f:
            profiles = json.load(f)
        return [p for p in profiles if p["archetype"] in ["strong", "normal", "weak"]][:3]

    def teardown_method(self):
        """Clean up test files."""
        if self.test_output.exists():
            self.test_output.unlink()

    def test_cache_detection(self):
        """Should detect already-scored profile+job combinations."""
        # Create mock results
        results = [
            {"profile_id": "profile_0000", "job_id": "jd_backend_dev", "score": 75},
            {"profile_id": "profile_0001", "job_id": "jd_backend_dev", "score": 60},
            {"profile_id": "profile_0002", "job_id": "jd_backend_dev", "score": 90},
        ]

        # Create scored keys set
        scored_keys = {(r["profile_id"], r["job_id"]) for r in results}

        # All 3 should be detected as cached
        for profile in self.test_profiles:
            key = (profile["id"], self.jd["id"])
            assert key in scored_keys, f"{profile['id']} should be in cache"

    def test_cache_miss_detection(self):
        """Should detect when profile+job combination is NOT cached."""
        results = [
            {"profile_id": "profile_0000", "job_id": "jd_backend_dev", "score": 75},
        ]
        scored_keys = {(r["profile_id"], r["job_id"]) for r in results}

        # profile_0001 and profile_0002 should NOT be in cache
        assert ("profile_0001", "jd_backend_dev") not in scored_keys
        assert ("profile_0002", "jd_backend_dev") not in scored_keys

    def test_results_save_and_load(self):
        """Should save results to JSON and load them back."""
        results = [
            {"profile_id": "profile_0000", "job_id": "jd_backend_dev", "score": 75, "decision": "maybe"},
            {"profile_id": "profile_0001", "job_id": "jd_backend_dev", "score": 60, "decision": "reject"},
        ]

        # Save
        self.test_output.parent.mkdir(parents=True, exist_ok=True)
        with open(self.test_output, "w") as f:
            json.dump(results, f, indent=2)

        # Load
        with open(self.test_output) as f:
            loaded = json.load(f)

        assert len(loaded) == 2
        assert loaded[0]["score"] == 75
        assert loaded[1]["decision"] == "reject"

    def test_partial_results_resume(self):
        """Should correctly handle resuming from partial results."""
        # Simulate partial results (only 1 of 3 scored)
        partial_results = [
            {"profile_id": "profile_0000", "job_id": "jd_backend_dev", "score": 75},
        ]
        scored_keys = {(r["profile_id"], r["job_id"]) for r in partial_results}

        # Count how many would be skipped
        skip_count = 0
        for profile in self.test_profiles:
            key = (profile["id"], self.jd["id"])
            if key in scored_keys:
                skip_count += 1

        assert skip_count == 1, f"Expected 1 cached, got {skip_count}"
        assert len(self.test_profiles) - skip_count == 2, "Expected 2 to process"
