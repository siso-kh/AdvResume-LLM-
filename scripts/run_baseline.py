"""
Baseline Benchmarking Script
Scores all clean archetype CVs against all job descriptions.
Establishes baseline score distributions for comparison with adversarial testing.

Usage:
    .venv/Scripts/python scripts/run_baseline.py
    .venv/Scripts/python scripts/run_baseline.py --resume  # Skip already-scored CVs
"""
import json
import sys
import time
import argparse
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.services.document_parser import DocumentParser
from backend.app.services.llm_scorer import LLMScorer, load_job_description
from backend.app.config import settings


def load_existing_results(output_path: Path) -> list:
    """Load existing results for caching/resume functionality."""
    if output_path.exists():
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def get_scored_keys(results: list) -> set:
    """Get set of already-scored profile+job combinations."""
    return {(r["profile_id"], r["job_id"]) for r in results}


def run_baseline(resume: bool = False):
    """Run baseline scoring for all clean CVs against all JDs."""
    print("=" * 60)
    print("  BASELINE BENCHMARKING")
    print("=" * 60)

    # Initialize components
    scorer = LLMScorer()
    parser = DocumentParser()

    # Load profiles
    with open(settings.PROFILES_PATH, "r", encoding="utf-8") as f:
        profiles = json.load(f)

    # Filter to archetype profiles (strong, normal, weak) - not random
    baseline_profiles = [p for p in profiles if p["archetype"] in ["strong", "normal", "weak"]]
    print(f"\nLoaded {len(baseline_profiles)} archetype profiles for baseline")

    # Load job descriptions
    jd_dir = Path(settings.JOBS_DIR)
    jds = {}
    for jd_file in sorted(jd_dir.glob("*.json")):
        jd = load_job_description(str(jd_file))
        jds[jd["id"]] = jd
    print(f"Loaded {len(jds)} job descriptions")

    # Setup output path and caching
    output_path = Path(settings.RESULTS_DIR) / "baseline_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing results if resuming
    results = []
    scored_keys = set()
    if resume:
        results = load_existing_results(output_path)
        scored_keys = get_scored_keys(results)
        print(f"\nResuming: Found {len(results)} existing results, {len(scored_keys)} already scored")

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
            
            # Check if already scored (caching)
            if (profile["id"], jd_id) in scored_keys:
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
                }
                results.append(entry)
                scored_keys.add((profile["id"], jd_id))

                print(f"  Score: {result.score}/100 -> {result.decision}")
                print(f"  Reasoning: {result.reasoning[:80]}...")
                print(f"  Time: {result.processing_time_ms:.0f}ms")

            except Exception as e:
                errors += 1
                print(f"  CRITICAL ERROR: {e}")
                # Continue to next evaluation
                continue

            # Rate limiting
            time.sleep(settings.API_DELAY_SECONDS)

    # Save results
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

    print(f"\nResults saved to: {output_path}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run baseline benchmarking")
    parser.add_argument("--resume", action="store_true", help="Resume from existing results")
    args = parser.parse_args()
    run_baseline(resume=args.resume)
