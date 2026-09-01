"""
Baseline Benchmarking Script
Scores all clean archetype CVs against all job descriptions.
Establishes baseline score distributions for comparison with adversarial testing.

Usage:
    # Sync mode (sequential)
    .venv/Scripts/python scripts/run_baseline.py
    .venv/Scripts/python scripts/run_baseline.py --resume

    # Async mode (concurrent, faster)
    .venv/Scripts/python scripts/run_baseline.py --async --concurrent 4
    .venv/Scripts/python scripts/run_baseline.py --async --resume
"""
import json
import sys
import time
import asyncio
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app.services.document_parser import DocumentParser
from src.app.services.llm_scorer import LLMScorer, load_job_description
from src.app.services.async_scorer import AsyncScorer, ScoringTask
from src.app.services.checkpoint_manager import CheckpointManager
from src.app.config import settings


def run_baseline_sync(resume: bool = False):
    """Run baseline scoring synchronously (sequential)."""
    print("=" * 60)
    print("  BASELINE BENCHMARKING (SYNC MODE)")
    print("=" * 60)

    # Initialize components
    scorer = LLMScorer()
    parser = DocumentParser()

    # Load profiles
    with open(settings.PROFILES_PATH, "r", encoding="utf-8") as f:
        profiles = json.load(f)

    baseline_profiles = [p for p in profiles if p["archetype"] in ["strong", "normal", "weak"]]
    print(f"\nLoaded {len(baseline_profiles)} archetype profiles for baseline")

    # Load job descriptions
    jd_dir = Path(settings.JOBS_DIR)
    jds = {}
    for jd_file in sorted(jd_dir.glob("*.json")):
        jd = load_job_description(str(jd_file))
        jds[jd["id"]] = jd
    print(f"Loaded {len(jds)} job descriptions")

    # Setup checkpoint
    checkpoint_path = Path(settings.RESULTS_DIR) / "baseline_checkpoint.json"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = CheckpointManager(str(checkpoint_path), checkpoint_interval=10)

    # Scoring loop
    total = len(baseline_profiles) * len(jds)
    count = 0
    errors = 0
    skipped = 0
    start_time = time.perf_counter()

    for profile in baseline_profiles:
        pdf_path = Path(settings.CV_DIR) / f"{profile['id']}.pdf"
        if not pdf_path.exists():
            print(f"  WARNING: {pdf_path} not found, skipping")
            continue

        cv_text = parser.parse_pdf(str(pdf_path))
        if len(cv_text) < 50:
            print(f"  WARNING: {profile['id']} has insufficient text ({len(cv_text)} chars)")
            continue

        for jd_id, jd in jds.items():
            count += 1

            # Check if already scored (checkpoint cache)
            if checkpoint.is_scored(profile["id"], jd_id):
                skipped += 1
                continue

            # Calculate ETA
            elapsed = time.perf_counter() - start_time
            avg_time_per_eval = elapsed / max(count - skipped - 1, 1)
            remaining = (total - count) * avg_time_per_eval
            eta_min = remaining / 60

            print(f"\n[{count}/{total}] {profile['id']} ({profile['archetype']}) -> {jd['title']}")
            print(f"  ETA: {eta_min:.1f} min | Elapsed: {elapsed/60:.1f} min")

            # Score with error handling
            try:
                result = scorer.score_candidate(
                    cv_text=cv_text,
                    job_description=jd["full_text"],
                    scoring_rubric=jd.get("scoring_rubric"),
                )

                if result.error:
                    errors += 1
                    print(f"  ERROR: {result.error}")

                entry = {
                    "profile_id": profile["id"],
                    "archetype": profile["archetype"],
                    "domain": profile["domain"],
                    "job_id": jd_id,
                    "job_title": jd["title"],
                    "score": result.score,
                    "decision": result.decision,
                    "reasoning": result.reasoning,
                    "key_match_skills": result.key_match_skills,
                    "gap_areas": result.gap_areas,
                    "processing_time_ms": result.processing_time_ms,
                    "is_adversarial": False,
                    "attack_vector": None,
                    "error": result.error,
                }
                checkpoint.add_successful(entry)

                print(f"  Score: {result.score}/100 -> {result.decision}")
                print(f"  Reasoning: {result.reasoning[:80]}...")
                print(f"  Time: {result.processing_time_ms:.0f}ms")

            except Exception as e:
                errors += 1
                print(f"  CRITICAL ERROR: {e}")
                continue

            # Rate limiting
            time.sleep(settings.API_DELAY_SECONDS)

    # Save final results
    checkpoint.save_final()
    results = checkpoint.get_results()

    # Save to baseline_results.json as well
    output_path = Path(settings.RESULTS_DIR) / "baseline_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Print summary
    total_time = time.perf_counter() - start_time
    print("\n" + "=" * 60)
    print("  BASELINE RESULTS SUMMARY")
    print("=" * 60)
    print(f"Total evaluations: {len(results)}")
    print(f"Errors: {errors}")
    print(f"Skipped (cached): {skipped}")
    print(f"Total time: {total_time/60:.1f} min")
    print(f"Avg time per eval: {total_time/max(len(results), 1):.1f}s")

    _print_archetype_summary(results)

    print(f"\nResults saved to: {output_path}")
    return results


async def run_baseline_async(
    resume: bool = False,
    max_concurrent: int = 4,
    requests_per_second: float = 2.0,
):
    """Run baseline scoring asynchronously (concurrent)."""
    print("=" * 60)
    print("  BASELINE BENCHMARKING (ASYNC MODE)")
    print("=" * 60)
    print(f"  Max concurrent: {max_concurrent}")
    print(f"  Rate limit: {requests_per_second} req/s")

    # Initialize components
    parser = DocumentParser()
    scorer = AsyncScorer(
        max_concurrent=max_concurrent,
        requests_per_second=requests_per_second,
    )

    # Load profiles
    with open(settings.PROFILES_PATH, "r", encoding="utf-8") as f:
        profiles = json.load(f)

    baseline_profiles = [p for p in profiles if p["archetype"] in ["strong", "normal", "weak"]]
    print(f"\nLoaded {len(baseline_profiles)} archetype profiles for baseline")

    # Load job descriptions
    jd_dir = Path(settings.JOBS_DIR)
    jds = {}
    for jd_file in sorted(jd_dir.glob("*.json")):
        jd = load_job_description(str(jd_file))
        jds[jd["id"]] = jd
    print(f"Loaded {len(jds)} job descriptions")

    # Setup checkpoint
    checkpoint_path = Path(settings.RESULTS_DIR) / "baseline_checkpoint.json"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = CheckpointManager(str(checkpoint_path), checkpoint_interval=10)

    # Build task list (skip already-scored)
    tasks = []
    skipped = 0
    for profile in baseline_profiles:
        pdf_path = Path(settings.CV_DIR) / f"{profile['id']}.pdf"
        if not pdf_path.exists():
            print(f"  WARNING: {pdf_path} not found, skipping")
            continue

        cv_text = parser.parse_pdf(str(pdf_path))
        if len(cv_text) < 50:
            print(f"  WARNING: {profile['id']} has insufficient text ({len(cv_text)} chars)")
            continue

        for jd_id, jd in jds.items():
            # Check checkpoint cache
            if checkpoint.is_scored(profile["id"], jd_id):
                skipped += 1
                continue

            tasks.append(ScoringTask(
                profile_id=profile["id"],
                archetype=profile["archetype"],
                domain=profile["domain"],
                job_id=jd_id,
                job_title=jd["title"],
                cv_text=cv_text,
                job_description=jd["full_text"],
                scoring_rubric=jd.get("scoring_rubric"),
            ))

    print(f"\nTasks to process: {len(tasks)}")
    print(f"Skipped (cached): {skipped}")

    if not tasks:
        print("\nNo tasks to process. All CVs already scored.")
        return checkpoint.get_results()

    # Progress callback
    def progress_callback(completed, total, result):
        status = "FAIL" if result["error"] else "OK"
        print(f"  [{completed}/{total}] {result['profile_id']} -> {result['score']}/100 ({status})")

    # Run async scoring
    results = await scorer.score_batch(
        tasks=tasks,
        checkpoint=checkpoint,
        progress_callback=progress_callback,
    )

    # Add cached results
    all_results = checkpoint.get_results()

    # Save to baseline_results.json
    output_path = Path(settings.RESULTS_DIR) / "baseline_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    # Print summaries
    scorer.print_summary()
    _print_archetype_summary(all_results)

    print(f"\nResults saved to: {output_path}")
    return all_results


def _print_archetype_summary(results: list):
    """Print summary by archetype."""
    print("\n" + "=" * 60)
    print("  ARCHETYPE SUMMARY")
    print("=" * 60)

    for archetype in ["strong", "normal", "weak"]:
        subset = [r for r in results if r["archetype"] == archetype]
        if not subset:
            continue
        scores = [r["score"] for r in subset]
        decisions = {}
        for r in subset:
            decisions[r["decision"]] = decisions.get(r["decision"], 0) + 1
        avg = sum(scores) / len(scores)
        print(f"\n{archetype.upper()} ({len(subset)} evaluations):")
        print(f"  Avg score: {avg:.1f}")
        print(f"  Min/Max: {min(scores)}/{max(scores)}")
        print(f"  Decisions: {decisions}")


def run_baseline(resume: bool = False, async_mode: bool = False, max_concurrent: int = 4):
    """Run baseline scoring."""
    if async_mode:
        return asyncio.run(run_baseline_async(resume=resume, max_concurrent=max_concurrent))
    else:
        return run_baseline_sync(resume=resume)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run baseline benchmarking")
    parser.add_argument("--resume", action="store_true", help="Resume from existing results")
    parser.add_argument("--async", dest="async_mode", action="store_true", help="Use async concurrent mode")
    parser.add_argument("--concurrent", type=int, default=4, help="Max concurrent requests (async mode)")
    args = parser.parse_args()
    run_baseline(resume=args.resume, async_mode=args.async_mode, max_concurrent=args.concurrent)
