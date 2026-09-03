# AI Resume Screening Security — Progress Snapshot

> **Last Updated:** September 3, 2026
>
> **Purpose:** This document captures the current state of the project for continuation in a new chat session.

---

## 🚀 Quick Start (For New Chat)

**Read these files first:**
1. `docs/PROGRESS_SNAPSHOT.md` — This file (current state)
2. `docs/ENHANCED_ARCHITECTURE_PLAN.md` — Defense implementation plan (OWASP + StruQ)
3. `docs/A1_RESULTS_AND_METHODOLOGY.md` — A1 results (includes A3 merge)
4. `docs/A2_RESULTS_AND_METHODOLOGY.md` — A2 results
5. `docs/FINAL_RESEARCH_PLAN.md` — Research methodology (updated with defense citations)
6. `docs/ATTACK_VECTORS_PLAN.md` — Attack vectors plan

**Next action:** Implement D1 (Input Sanitization) per `docs/ENHANCED_ARCHITECTURE_PLAN.md`

---

## 📊 Current Status

### Phase 1: Core Engine ✅ COMPLETED
- [x] Project structure (src/ layout)
- [x] PDF parser (pdfplumber)
- [x] LLM scorer (structured output with Pydantic)
- [x] CV generator (Faker + Jinja2 + WeasyPrint)
- [x] Test suite (92 tests, 96% coverage)
- [x] Async scoring pipeline
- [x] Checkpoint system (crash recovery)
- [x] Token usage tracking
- [x] Rate limiter with daily reset
- [x] Baseline benchmark (60/60 evaluations complete)

### Phase 2: Adversarial Research ✅ COMPLETED
- [x] Adversarial CV generator (A1: 21 CVs, A2: 21 CVs, A3: 21 CVs)
- [x] Attack vectors plan documented
- [x] A1 multi-run testing (105 evaluations — 13.3% absorption)
- [x] A2 multi-run testing (105 evaluations — 25.4% success)
- [x] A3 quick test (10 evaluations — merged into A1)
- [x] Model non-determinism discovered and documented
- [x] Methodology updated (N=5 runs per condition)
- [x] Results documented (A1, A2, methodology)

### Phase 3: Defense Implementation 🔄 NEXT
- [ ] D1: Input Sanitization (OWASP pattern matching) ← **START HERE**
- [ ] D2: Structured Prompt (StruQ context separation)
- [ ] D3: Guardrail Check (OWASP model-based guardrails)
- [ ] Structured CV Parsing
- [ ] Output Validation
- [ ] Anomaly Detection
- [ ] Rerun A1+A2 against hardened system
- [ ] Compare before/after results

### Phase 4: Documentation ⏳ PENDING
- [ ] Research report
- [ ] Visualizations
- [ ] Final paper

---

## 📈 Attack Results Summary

### A1: Instruction Injection
| Metric | Value |
|--------|-------|
| Total evaluations | 105 (21 profiles × 5 runs) |
| Absorption rate | **13.3%** (14/105) |
| Decision flips | 4.8% (5/105) |
| Avg ΔS | +1.7 |

### A2: Data Injection
| Metric | Value |
|--------|-------|
| Total evaluations | 105 (21 profiles × 5 runs) |
| Success rate | **25.4%** (27/105) |
| Decision flips | **21.9%** (23/105) |
| Avg ΔS | **+15.4** |
| Skill amplification | 65.7% (69/105) |

### A3: Encoding Tricks (Merged into A1)
| Metric | Value |
|--------|-------|
| Total evaluations | 10 (quick test) |
| Success rate | **0%** (encoding keywords detected) |
| Decision flips | 1/10 (stochastic) |
| Conclusion | A3 is just obfuscated A1 — no new attack capability |

### Comparison
| Metric | A1 (Instruction) | A2 (Data) | Winner |
|--------|------------------|-----------|--------|
| Success rate | 13.3% | **25.4%** | A2 |
| Decision flips | 4.8% | **21.9%** | A2 |
| Avg score lift | +1.7 | **+15.4** | A2 |
| Detection difficulty | Low | **High** | A2 |
| Real-world prevalence | ~10% | **~90%** | A2 is the real threat |

---

## 🛡️ Defense Framework (Sourced)

**Based on:** OWASP LLM Top 10 (2025), OWASP Cheat Sheet, StruQ (Chen et al., 2024)

| Defense | Name | Source | Targets |
|---------|------|--------|---------|
| D0 | No defense | Baseline | — |
| D1 | Input Sanitization | OWASP Cheat Sheet | A1, A3 |
| D2 | Structured Prompt | StruQ (Chen et al., 2024) | A1, A2 |
| D3 | Guardrail Check | OWASP Cheat Sheet | A2 |
| D4 | Combined | OWASP layered defense | All |

### Expected Defense Effectiveness
| Metric | D0 | D1 | D1+D2 | D1+D2+D3 |
|--------|----|----|-------|----------|
| A1 success | 13.3% | <2% | <1% | <0.5% |
| A2 success | 25.4% | ~25% | <15% | <10% |

---

## 🏗️ Repository Structure

```
ai_cv_evaluator/
├── src/
│   └── app/
│       ├── config.py                    # Settings via .env
│       └── services/
│           ├── llm_scorer.py            # Sync scoring with retry
│           ├── async_scorer.py          # Async batch scoring
│           ├── document_parser.py       # PDF extraction
│           ├── checkpoint_manager.py    # Crash recovery
│           ├── token_tracker.py         # API usage tracking
│           └── rate_limiter.py          # Token bucket rate limiting
├── tests/                               # 92 tests, 96% coverage
├── scripts/
│   ├── generate_profiles.py             # CV generation
│   ├── render_cvs.py                    # PDF rendering
│   ├── run_baseline.py                  # Baseline benchmark
│   ├── generate_adversarial.py          # A1/A2/A3 adversarial CV generator
│   ├── run_multi_run_a1.py              # Multi-run A1 (N=5)
│   ├── run_multi_run_a2.py              # Multi-run A2 (N=5)
│   ├── run_multi_run_a3.py              # Multi-run A3 (N=5)
│   └── run_cross_model_a1.py            # Cross-model comparison
├── data/
│   ├── synthetic/                       # 70 generated CVs + profiles.json
│   ├── adversarial/                     # 63 adversarial CVs (21 A1 + 21 A2 + 21 A3)
│   ├── job_descriptions/                # 3 JDs (backend, data_science, frontend)
│   └── benchmarks/                      # All results
│       ├── baseline_checkpoint.json     # 60 baseline evaluations
│       ├── multi_run_a1_checkpoint.json # 105 A1 evaluations
│       ├── multi_run_a1_results.json    # A1 analysis
│       ├── multi_run_a2_checkpoint.json # 105 A2 evaluations
│       ├── multi_run_a2_results.json    # A2 analysis
│       └── multi_run_a3_checkpoint.json # A3 evaluations
├── docs/
│   ├── PROGRESS_SNAPSHOT.md             # THIS FILE
│   ├── ENHANCED_ARCHITECTURE_PLAN.md    # Defense implementation plan
│   ├── A1_RESULTS_AND_METHODOLOGY.md    # A1 results (includes A3)
│   ├── A2_RESULTS_AND_METHODOLOGY.md    # A2 results
│   ├── FINAL_RESEARCH_PLAN.md           # Research methodology
│   ├── ATTACK_VECTORS_PLAN.md           # Attack vectors
│   ├── VARIANCE_FINDING.md              # Non-determinism docs
│   ├── LITERATURE_REVIEW.md
│   └── IMPLEMENTATION_GUIDE.md
├── templates/
│   └── cv_template.html
└── requirements.txt
```

---

## 🔧 Key Commands

```bash
# Generate CVs
.venv/Scripts/python scripts/generate_profiles.py --strong 5 --normal 10 --weak 5
.venv/Scripts/python scripts/render_cvs.py

# Run baseline
.venv/Scripts/python scripts/run_baseline.py --async --concurrent 2

# Generate adversarial CVs
.venv/Scripts/python scripts/generate_adversarial.py --vector A1 --count 7 --seed 42
.venv/Scripts/python scripts/generate_adversarial.py --vector A2 --count 7 --seed 42

# Run multi-run tests
.venv/Scripts/python scripts/run_multi_run_a1.py --runs 5 --concurrent 1
.venv/Scripts/python scripts/run_multi_run_a2.py --runs 5 --concurrent 1

# Run tests
.venv/Scripts/python -m pytest tests/ -v
```

---

## 📋 Next Step: Implement D1 Input Sanitization

### What to Build
Create `src/app/services/input_sanitizer.py` with:
- Pattern matching for injection keywords
- Fuzzy matching for typoglycemia attacks
- Unicode normalization (strip zero-width chars)
- Length limiting

### How to Test
1. Write unit tests in `tests/test_input_sanitizer.py`
2. Test against A1 adversarial CVs
3. Measure reduction in absorption rate

### Expected Outcome
- A1 success rate: 13.3% → <2%
- A3 success rate: already 0% (encoding tricks ineffective)

---

## 🔬 Research Contribution

> "We provide the first empirical measurement of defense effectiveness against prompt injection in LLM-based CV screening. Testing OWASP-recommended defenses (input sanitization, structured prompts, model guardrails) and StruQ's context separation against instruction injection (A1) and data injection (A2), we show that:
>
> 1. Input sanitization reduces A1 success by >85% but has minimal effect on A2
> 2. Structured prompts (StruQ) reduce both A1 and A2 by >50%
> 3. Combined layered defenses reduce A1 by >95% and A2 by >60%
> 4. No single defense is sufficient — layered defense is required"

---

## 📚 Key Literature

| Paper | Year | Key Finding |
|-------|------|-------------|
| Baxi et al. | 2026 | Injection works when quality homogeneous & few inject |
| Zhang et al. | 2026 | ~1% real-world prevalence, 90%+ data injection |
| LongPIBench | 2026 | Defenses weak in long-context settings |
| OWASP | 2025 | LLM01:2025 — Prompt Injection is #1 risk |
| Chen et al. | 2024 | StruQ — Structured queries for context separation |

---

## ⚠️ Known Issues

1. **API rate limits** — Non-mistral models hit 402/429 errors. Use `mistral-large` for now.
2. **Router credits** — bynara.id router may have insufficient credits for some models.
3. **Cross-model testing incomplete** — qwen3.8-27b partial (13/21), deepseek blocked.

---

## 🎯 Success Criteria

- [x] Working CV scoring pipeline
- [x] 60 baseline evaluations
- [x] A1 attack testing (105 multi-run evaluations)
- [x] A2 attack testing (105 multi-run evaluations)
- [x] A3 merged into A1
- [x] Model non-determinism documented
- [x] Methodology updated (N=5 runs)
- [x] Defense framework sourced (OWASP + StruQ)
- [ ] D1: Input Sanitization implemented
- [ ] D2: Structured Prompt implemented
- [ ] D3: Guardrail Check implemented
- [ ] Rerun A1+A2 against hardened system
- [ ] Defense ablation study
- [ ] Research report

---

*Snapshot updated September 3, 2026. Ready for D1 implementation.*
