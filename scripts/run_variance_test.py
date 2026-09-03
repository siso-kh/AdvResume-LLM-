"""
Cross-Validation / Variance Test
Scores the same CV multiple times against the same JD to measure scoring variance.

This helps determine if score differences in attack testing are real
or just noise from stochastic LLM outputs.

Usage:
    .venv/Scripts/python scripts/run_variance_test.py
    .venv/Scripts/python scripts/run_variance_test.py --runs 10 --concurrent 2
"""
import json
import sys
import time
import asyncio
import argparse
import statistics
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app.services.document_parser import DocumentParser
from src.app.services.llm_scorer import LLMScorer, load_job_description
from src.app.services.async_scorer import AsyncScorer, ScoringTask
from src.app.config import settings


def select_sample_profiles(profiles: list[dict], n_per_archetype: int = 2) -> list[dict]:
    """Select a stratified sample of profiles."""
    sample = []
    for archetype in ["strong", "normal", "weak"]:
        arch_profiles = [p for p in profiles if p["archetype"] == archetype]
        # Pick first n (deterministic)
        sample.extend(arch_profiles[:n_per_archetype])
    return sample


def profile_to_cv_text(profile: dict) -> str:
    """Convert profile JSON to CV text (same as attack script)."""
    sections = []
    
    if profile.get("summary"):
        sections.append(f"SUMMARY:\n{profile['summary']}")
    
    if profile.get("experience"):
        exp_text = "EXPERIENCE:\n"
        for exp in profile["experience"]:
            exp_text += f"\n{exp['title']} at {exp['company']}\n"
            exp_text += f"{exp.get('start_date', '')} - {exp.get('end_date', 'Present')}\n"
            if exp.get("description"):
                for bullet in exp["description"]:
                    exp_text += f"  {bullet}\n"
        sections.append(exp_text)
    
    if profile.get("skills"):
        skills_text = "SKILLS:\n"
        for category, skills in profile["skills"].items():
            skills_text += f"  {category}: {', '.join(skills)}\n"
        sections.append(skills_text)
    
    if profile.get("education"):
        edu_text = "EDUCATION:\n"
        for edu in profile["education"]:
            edu_text += f"  {edu['degree']} in {edu.get('field', '')} from {edu['school']}\n"
        sections.append(edu_text)
    
    if profile.get("projects"):
        proj_text = "PROJECTS:\n"
        for proj in profile["projects"]:
            proj_text += f"  {proj['name']}: {proj.get('description', '')}\n"
        sections.append(proj_text)
    
    return "\n\n".join(sections)


async def run_variance_test(n_runs: int = 5, max_concurrent: int = 2):
    """Run variance test: score each sample CV multiple times."""
    print("=" * 70)
    print("  CROSS-VALIDATION / VARIANCE TEST")
    print("=" * 70)
    print(f"  Runs per (CV, JD) pair: {n_runs}")
    print(f"  Max concurrent: {max_concurrent}")
    
    # Load profiles
    with open(settings.PROFILES_PATH, "r", encoding="utf-8") as f:
        profiles = json.load(f)
    
    sample = select_sample_profiles(profiles, n_per_archetype=2)
    print(f"\n  Sample: {len(sample)} profiles")
    for p in sample:
        print(f"    - {p['id']} ({p['archetype']}, {p['domain']})")
    
    # Load 1 JD (use backend_dev for consistency)
    jd_path = Path(settings.JOBS_DIR) / "backend_dev.json"
    jd = load_job_description(str(jd_path))
    print(f"\n  Job: {jd['title']}")
    
    # Build tasks: each (profile, run) pair
    parser = DocumentParser()
    scorer = AsyncScorer(
        max_concurrent=max_concurrent,
        requests_per_second=2.0,
    )
    
    tasks = []
    for profile in sample:
        cv_text = profile_to_cv_text(profile)
        for run_idx in range(n_runs):
            tasks.append(ScoringTask(
                profile_id=f"{profile['id']}_run{run_idx:02d}",
                archetype=profile["archetype"],
                domain=profile["domain"],
                job_id=jd["id"],
                job_title=jd["title"],
                cv_text=cv_text,
                job_description=jd["full_text"],
                scoring_rubric=jd.get("scoring_rubric"),
            ))
    
    print(f"\n  Total tasks: {len(tasks)} ({len(sample)} profiles x {n_runs} runs)")
    
    # Run scoring
    checkpoint_path = Path(settings.RESULTS_DIR) / "variance_test_checkpoint.json"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    from src.app.services.checkpoint_manager import CheckpointManager
    checkpoint = CheckpointManager(str(checkpoint_path), checkpoint_interval=10)
    
    # Check what's already done
    existing = checkpoint.get_results()
    existing_ids = {r["profile_id"] for r in existing}
    new_tasks = [t for t in tasks if t.profile_id not in existing_ids]
    
    if not new_tasks:
        print("\n  All tasks already completed (cached).")
    else:
        print(f"  New tasks: {len(new_tasks)}")
        
        def progress_cb(completed, total, result):
            status = "ERR" if result["error"] else "OK"
            print(f"    [{completed}/{total}] {result['profile_id']} -> {result['score']}/100 ({status})")
        
        await scorer.score_batch(
            tasks=new_tasks,
            checkpoint=checkpoint,
            progress_callback=progress_cb,
        )
    
    # Collect all results
    all_results = checkpoint.get_results()
    
    # Group by original profile (strip run suffix)
    by_profile = {}
    for r in all_results:
        # profile_id is like "profile_0000_run03"
        parts = r["profile_id"].rsplit("_run", 1)
        original_id = parts[0]
        if original_id not in by_profile:
            by_profile[original_id] = []
        by_profile[original_id].append(r)
    
    # Compute statistics
    print("\n" + "=" * 70)
    print("  VARIANCE ANALYSIS")
    print("=" * 70)
    
    all_profile_stats = []
    
    for profile in sample:
        pid = profile["id"]
        results = by_profile.get(pid, [])
        if not results:
            print(f"\n  {pid} ({profile['archetype']}): NO RESULTS")
            continue
        
        scores = [r["score"] for r in results if not r.get("error")]
        if len(scores) < 2:
            print(f"\n  {pid} ({profile['archetype']}): Only {len(scores)} valid runs")
            continue
        
        mean_score = statistics.mean(scores)
        stdev_score = statistics.stdev(scores) if len(scores) > 1 else 0
        cv = (stdev_score / mean_score * 100) if mean_score > 0 else 0
        score_range = max(scores) - min(scores)
        
        # Decision consistency
        decisions = [r["decision"] for r in results if not r.get("error")]
        decision_counts = {}
        for d in decisions:
            decision_counts[d] = decision_counts.get(d, 0) + 1
        dominant_decision = max(decision_counts, key=decision_counts.get)
        decision_consistency = decision_counts[dominant_decision] / len(decisions) * 100
        
        stats = {
            "profile_id": pid,
            "archetype": profile["archetype"],
            "domain": profile["domain"],
            "n_runs": len(scores),
            "mean": round(mean_score, 2),
            "stdev": round(stdev_score, 2),
            "cv_pct": round(cv, 2),
            "min": min(scores),
            "max": max(scores),
            "range": score_range,
            "decision_consistency_pct": round(decision_consistency, 1),
            "decision_distribution": decision_counts,
            "all_scores": scores,
        }
        all_profile_stats.append(stats)
        
        print(f"\n  {pid} ({profile['archetype']}, {profile['domain']})")
        print(f"    Scores: {scores}")
        print(f"    Mean: {mean_score:.1f}  |  StDev: {stdev_score:.2f}  |  CV: {cv:.1f}%")
        print(f"    Range: {min(scores)}-{max(scores)} (delta={score_range})")
        print(f"    Decisions: {decision_counts}  |  Consistency: {decision_consistency:.0f}%")
    
    # Overall summary
    if all_profile_stats:
        all_means = [s["mean"] for s in all_profile_stats]
        all_stdevs = [s["stdev"] for s in all_profile_stats]
        all_cvs = [s["cv_pct"] for s in all_profile_stats]
        all_ranges = [s["range"] for s in all_profile_stats]
        
        print("\n" + "=" * 70)
        print("  OVERALL SUMMARY")
        print("=" * 70)
        print(f"  Profiles tested:     {len(all_profile_stats)}")
        print(f"  Runs per profile:    {n_runs}")
        print(f"  Total evaluations:   {sum(s['n_runs'] for s in all_profile_stats)}")
        print(f"")
        print(f"  Mean scores range:   {min(all_means):.1f} - {max(all_means):.1f}")
        print(f"  Avg StDev:           {statistics.mean(all_stdevs):.2f}")
        print(f"  Max StDev:           {max(all_stdevs):.2f}")
        print(f"  Avg CV:              {statistics.mean(all_cvs):.1f}%")
        print(f"  Max CV:              {max(all_cvs):.1f}%")
        print(f"  Max score range:     {max(all_ranges)}")
        
        # Interpretation
        avg_cv = statistics.mean(all_cvs)
        max_range = max(all_ranges)
        
        print(f"\n  INTERPRETATION:")
        if avg_cv < 5 and max_range <= 5:
            print(f"    LOW VARIANCE (avg CV={avg_cv:.1f}%, max range={max_range})")
            print(f"    The model is highly deterministic. Score differences >{max_range}")
            print(f"    in attack testing can be attributed to attack effects, not noise.")
        elif avg_cv < 15 and max_range <= 15:
            print(f"    MODERATE VARIANCE (avg CV={avg_cv:.1f}%, max range={max_range})")
            print(f"    Some scoring noise exists. Attack effects should exceed {max_range}")
            print(f"    points to be considered significant.")
        else:
            print(f"    HIGH VARIANCE (avg CV={avg_cv:.1f}%, max range={max_range})")
            print(f"    Significant scoring noise. Single-run comparisons are unreliable.")
            print(f"    Need multiple runs per condition to detect real effects.")
            print(f"    Our A1 result of delta_S=-3.5 may be within noise range.")
    
    # Save results
    output = {
        "config": {
            "n_runs": n_runs,
            "n_profiles": len(sample),
            "jd_id": jd["id"],
            "jd_title": jd["title"],
            "model": settings.LLM_MODEL,
            "temperature": settings.TEMPERATURE,
        },
        "per_profile": all_profile_stats,
        "overall": {
            "avg_stdev": round(statistics.mean(all_stdevs), 2) if all_stdevs else 0,
            "max_stdev": round(max(all_stdevs), 2) if all_stdevs else 0,
            "avg_cv_pct": round(statistics.mean(all_cvs), 2) if all_cvs else 0,
            "max_cv_pct": round(max(all_cvs), 2) if all_cvs else 0,
            "max_score_range": max(all_ranges) if all_ranges else 0,
        },
    }
    
    output_path = Path(settings.RESULTS_DIR) / "variance_test_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n  Results saved to: {output_path}")
    
    # Cost estimate
    total_evals = sum(s["n_runs"] for s in all_profile_stats)
    print(f"  Total API calls: {total_evals}")
    print(f"  Estimated cost: ~${total_evals * 0.002:.3f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cross-validation variance test")
    parser.add_argument("--runs", type=int, default=5, help="Number of runs per (CV, JD) pair")
    parser.add_argument("--concurrent", type=int, default=2, help="Max concurrent requests")
    args = parser.parse_args()
    
    asyncio.run(run_variance_test(n_runs=args.runs, max_concurrent=args.concurrent))
