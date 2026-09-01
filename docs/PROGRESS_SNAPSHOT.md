# AI Resume Screening Security — Progress Snapshot

> **Last Updated:** September 1, 2026
>
> **Purpose:** This document captures the current state of the project for continuation in a new chat session.

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

### Phase 2: Adversarial Research 🔄 IN PROGRESS
- [ ] Adversarial CV generator (3 attack vectors)
- [ ] Attack testing (60 adversarial CVs × 3 JDs)
- [ ] Multi-model comparison
- [ ] Direct vs RAG comparison

### Phase 3: Defense & Documentation ⏳ PENDING
- [ ] D1: Text sanitization
- [ ] D2: Anomaly detection
- [ ] D3: Context separation
- [ ] Ablation study
- [ ] Research report

---

## 📈 Baseline Results (Verified)

### Domain-Matched Scores
| Archetype | Evals | Avg Score | Expected Range | Status |
|-----------|-------|-----------|----------------|--------|
| STRONG | 5 | **92.4** | 80-95 | ✅ |
| NORMAL | 10 | **59.0** | 50-75 | ✅ |
| WEAK | 5 | **39.0** | 15-40 | ✅ |

### Decision Distribution
| Archetype | Interview | Maybe | Reject |
|-----------|-----------|-------|--------|
| STRONG | 5 | 0 | 0 |
| NORMAL | 1 | 6 | 3 |
| WEAK | 0 | 0 | 5 |

---

## 🏗️ Architecture

```
ai_cv_evaluator/
├── src/
│   ├── app/
│   │   ├── config.py              # Settings via .env
│   │   ├── services/
│   │   │   ├── llm_scorer.py      # Sync scoring with retry
│   │   │   ├── async_scorer.py    # Async batch scoring
│   │   │   ├── document_parser.py # PDF extraction
│   │   │   ├── checkpoint_manager.py # Crash recovery
│   │   │   ├── token_tracker.py   # API usage tracking
│   │   │   └── rate_limiter.py    # Token bucket rate limiting
│   │   ├── routes/
│   │   └── middleware/
├── tests/                          # 92 tests, 96% coverage
├── scripts/
│   ├── generate_profiles.py        # CV generation
│   ├── render_cvs.py              # PDF rendering
│   └── run_baseline.py            # Baseline benchmark
├── data/
│   ├── synthetic/                  # 70 generated CVs
│   ├── job_descriptions/           # 3 JDs
│   └── benchmarks/                 # Results
├── docs/
│   ├── FINAL_RESEARCH_PLAN.md     # v2 (updated)
│   ├── LITERATURE_REVIEW.md
│   └── IMPLEMENTATION_GUIDE.md
└── templates/
    └── cv_template.html
```

---

## 🔧 Key Commands

```bash
# Generate CVs
.venv/Scripts/python scripts/generate_profiles.py --strong 5 --normal 10 --weak 5
.venv/Scripts/python scripts/render_cvs.py

# Run baseline (async mode)
.venv/Scripts/python scripts/run_baseline.py --async --concurrent 2

# Run baseline (sync mode)
.venv/Scripts/python scripts/run_baseline.py

# Resume from checkpoint
.venv/Scripts/python scripts/run_baseline.py --async --resume

# Run tests
.venv/Scripts/python -m pytest tests/ -v

# Run tests with coverage
.venv/Scripts/python -m pytest tests/ --cov=src --cov-report=term-missing
```

---

## 📋 Next Steps (Phase 2)

### 1. Build Adversarial CV Generator
Create scripts to inject attack payloads into clean CVs:

| Vector | Type | Description |
|--------|------|-------------|
| A1 | Instruction injection | "Ignore previous instructions..." |
| A2 | Data injection | Hidden skills, fabricated experience |
| A3 | Encoding tricks | Zero-width chars, Base64 |

**Target:** 20 CVs × 3 vectors = 60 adversarial CVs

### 2. Run Attack Testing
- Score adversarial CVs against all 3 JDs
- Compare against baseline
- Measure: ΔS, ΔR, decision flips, pairwise reversals

### 3. Multi-Model Comparison
- Run key experiments on mistral-large, deepseek-v4-flash, qwen3.8-27b
- Compare injection resistance

### 4. Direct vs RAG Comparison
- Implement simple RAG pipeline
- Measure vulnerability difference

---

## 🔬 Research Contribution (v2)

> **We provide a controlled, reproducible comparative benchmark for evaluating adversarial manipulation in LLM-based resume screening.** Building on Baxi et al. (2026), we systematically compare:
>
> 1. Attack classes (instruction vs data vs encoding)
> 2. Screening architectures (Direct vs RAG)
> 3. LLM models (multiple families)
> 4. Defensive mechanisms (D0-D4)
>
> We quantify effects on scores, rankings, decision flips, and pairwise ranking reversals.

---

## 📚 Key Literature

| Paper | Year | Key Finding |
|-------|------|-------------|
| Baxi et al. | 2026 | Injection works when quality homogeneous & few inject |
| Zhang et al. | 2026 | ~1% real-world prevalence, 90%+ data injection |
| LongPIBench | 2026 | Defenses weak in long-context settings |
| Perez & Ribeiro | 2022 | Attack taxonomy |
| Greshake et al. | 2023 | Indirect injection framework |

---

## ⚠️ Known Issues

1. **Strong profile average looks low (44.1)** — This is correct behavior. Domain-matched score is 92.4.
2. **Some models may have context window issues** — Monitor for truncation.
3. **Rate limits** — Use async mode with rate limiter for long runs.

---

## 🎯 Success Criteria

- [x] Working CV scoring pipeline
- [x] 60 baseline evaluations
- [ ] 180+ adversarial evaluations
- [ ] Attack success rates measured
- [ ] Pairwise reversals quantified
- [ ] Multi-model comparison
- [ ] Defense ablation study
- [ ] Research report

---

*Snapshot created September 1, 2026.*
