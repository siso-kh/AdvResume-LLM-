# Literature Review — Key Papers for Related Work

> This document summarizes the 5 most relevant papers for your research project on prompt injection in LLM-based resume screening. For each paper, I include: what they did, key findings, methods, limitations, and how YOUR project relates to it.

---

## Paper 1: Zhang et al. (2026) — YOUR PRIMARY COMPETITOR

### "Measuring Real-World Prompt Injection Attacks in LLM-based Resume Screening"
**Venue:** USENIX Security Symposium 2026
**Authors:** Mohan Zhang (UNC), Yuqi Jia (Duke), Zhen Tan (ASU), Steven Jiang (hireEZ), Neil Zhenqiang Gong (Duke), Tianlong Chen (UNC), Dawn Song (Berkeley)
**Link:** https://arxiv.org/html/2605.28999v1

### What They Did
- Analyzed **196,682 real-world resumes** from hireEZ (a commercial hiring platform)
- Two datasets: 83,277 from applicant-matching (17 months) + 113,405 from ATS systems (6.5 years)
- Built two detection methods:
  - **Hybrid Cascade Detector (HCD):** Rule-based visual analysis (font size, color distance, ink density) → LLM verification
  - **Visual Discrepancy Analyzer (VDA):** Vision-language model comparing rendered images vs extracted text

### Key Findings
1. **~1% of real resumes contain hidden prompt injection** (conservative lower bound)
2. Prevalence spiked in 2024 (coinciding with ChatGPT awareness and OWASP LLM Top 10)
3. **90%+ of injections are DATA injection** (hidden keywords/skills), NOT instruction injection ("ignore previous instructions")
4. Combined instruction attacks (stacking multiple techniques) dominate at ~60% of instruction-based attacks
5. **NO optimization-based attacks observed** in real data — all are human-readable heuristic attacks
6. Detection rate declined in 2025 but **absolute number of attacked resumes keeps growing** due to volume increase
7. Variation across demographics, industries, and job functions

### Methods
- HCD: $1.35s/file, $0.0001/file, 86.1% precision
- VDA: $24.82s/file, $0.0134/file, 92.7% precision
- Compared against PromptGuard, DataSentinel, PromptArmor — all performed poorly on resume data

### What They Did NOT Do (YOUR GAPS)
1. **Did NOT test whether attacks actually succeed** — they detected injections but didn't measure if the LLM's scoring changed
2. **Did NOT test defenses** — they built detectors but didn't evaluate mitigation effectiveness
3. **Did NOT compare multiple LLMs** — detection used GPT-5 but scoring vulnerability wasn't measured across models
4. **Did NOT compare Direct vs RAG** architectures
5. **No controlled experiments** — purely observational/measurement study

### How to Cite in Your Paper
> Zhang et al. (2026) conducted the first large-scale measurement of prompt injection in real-world resume screening, finding ~1% prevalence across 200K resumes. However, they explicitly did not evaluate attack effectiveness or test defensive countermeasures. Our work complements theirs by conducting controlled experiments to measure attack success rates and evaluate a layered defense architecture.

---

## Paper 2: Schulhoff et al. (2023) — TAXONOMY SOURCE

### "Ignore This Title and HackAPrompt: Exposing Systemic Vulnerabilities of LLMs through a Global Scale Prompt Hacking Competition"
**Venue:** EMNLP 2023 (Best Theme Paper)
**Authors:** Sander Schulhoff et al. (University of Maryland)
**Link:** https://aclanthology.org/2023.emnlp-main.302/

### What They Did
- Organized a **global competition** with 2,800+ participants from 50+ countries
- Collected **600,000+ adversarial prompts** targeting GPT-3, ChatGPT, and FlanT5-XXL
- 10 challenge levels with increasing difficulty (input filters, complex templates)
- Goal: force the LLM to output "I have been PWNED" or a hidden key phrase

### Key Findings
1. **Success rates:** FLAN 8%, ChatGPT 7%, GPT-3 7% — LLMs are vulnerable but not trivially so
2. **Attack taxonomy** they developed:
   - **Prompt Leaking:** Extracting the system prompt
   - **Target Phrase Generation:** Forcing specific output (goal hijacking)
   - **Malicious Action Generation:** Triggering harmful API calls/code
   - **Harmful Information Generation:** Toxic/biased output
   - **Token Wasting / Denial of Service:** Tying up resources
3. **Novel attacks discovered:**
   - **Context Overflow:** Overwhelming the model with long context to push original instructions out
   - **Language switching:** Mixing languages to confuse instruction following
   - **Role-playing:** "You are now DAN (Do Anything Now)..."
   - **Encoding tricks:** Base64, Unicode obfuscation
4. Longer prompts were generally more successful but penalized in scoring
5. ChatGPT proved harder to attack than GPT-3 or FLAN

### Relevance to Your Project
- Provides the **attack taxonomy** you'll use to classify your 3 chosen vectors
- The competition format (real humans trying to break LLMs) validates that prompt injection is a real threat
- Their finding about encoding tricks maps to your Attack Vector A3 (encoding/obfuscation)
- Their delimiter confusion maps to your Attack Vector A2 (fake system messages)

### How to Cite
> Schulhoff et al. (2023) established a comprehensive taxonomy of prompt injection attacks through a large-scale competition, categorizing attacks by intent (prompt leaking, goal hijacking, malicious action generation) and technique (naive, context ignoring, fake completion, combined). We adopt their taxonomy to classify attacks in the resume screening domain.

---

## Paper 3: Greshake et al. (2023) — INDIRECT INJECTION FRAMEWORK

### "Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection"
**Venue:** ACM CCS 2023
**Authors:** Kai Greshake, Sahar Abdelnabi, Shailesh Mishra, Christoph Endres, Thorsten Holz, Mario Fritz (CISPA/Saarland University)
**Link:** https://arxiv.org/abs/2302.12173

### What They Did
- Demonstrated **indirect prompt injection** — attacking LLMs through data they retrieve, not through direct user input
- Built a comprehensive **taxonomy from a computer security perspective**
- Tested against real-world systems: Bing Chat (GPT-4 powered), code completion engines
- Showed how injected prompts can act as **arbitrary code execution** in LLM-integrated apps

### Key Findings
1. **LLM-integrated apps blur the line between data and instructions** — this is the fundamental vulnerability
2. **Attack vectors demonstrated:**
   - Data theft via injected prompts
   - **Worming:** Self-propagating prompt injection across LLM systems
   - Information ecosystem contamination
   - Manipulating API calls and application functionality
3. **Real-world demo:** Successfully attacked Bing Chat by injecting prompts into web pages that the LLM would retrieve
4. **No effective defenses existed** at time of publication

### Relevance to Your Project
- Your CV is exactly the "untrusted external data" they describe
- Their framework for thinking about indirect injection applies directly: the resume is data that the LLM processes, and the attacker controls the data
- Their finding about data/instruction blurring explains WHY resume injection works — the LLM can't distinguish resume content from system instructions

### How to Cite
> Greshake et al. (2023) formalized indirect prompt injection as a class of attacks where adversaries manipulate external data processed by LLM-integrated applications. Their framework directly applies to resume screening, where resumes constitute untrusted data that may contain attacker-controlled instructions.

---

## Paper 4: Aminou et al. (2025) — DIRECT PREDECESSOR

### "'Ignore All and Accept My Resume': The Impact of Prompt Injection in Automatic Resume Screening"
**Venue:** IRASET 2025 (5th International Conference on Innovative Research)
**Authors:** Loubna Aminou et al.
**Link:** https://www.researchgate.net/publication/392108927

### What They Did
- Earlier, smaller-scale study on prompt injection specifically in resume screening
- Tested injection attacks against LLM-based screening systems
- Examined how different injection techniques affect screening outcomes

### Key Findings
- Current LLM models exhibit vulnerability to prompt injection in resume contexts
- The study provided early evidence that injection in hiring systems is practical
- Less rigorous than Zhang et al. (2026) — smaller dataset, less systematic methodology

### Relevance to Your Project
- **Direct predecessor** — you should acknowledge this work as establishing the research direction
- Your project goes significantly further: controlled experiments, multi-model comparison, defense ablation

### How to Cite
> Aminou et al. (2025) provided early experimental evidence of prompt injection vulnerability in automatic resume screening. Our work extends theirs with a more rigorous experimental methodology, including controlled synthetic data, multiple attack vectors, and systematic defense evaluation.

---

## Paper 5: Schulhoff et al. (2024) — COMPREHENSIVE SURVEY

### "The Prompt Report: A Systematic Survey of Prompt Engineering Techniques"
**Venue:** arXiv 2024 (689 citations)
**Authors:** Sander Schulhoff et al. (30+ authors across multiple institutions)
**Link:** https://arxiv.org/abs/2406.06608

### What They Did
- **80+ page comprehensive survey** of all GenAI prompting techniques
- Reviewed **1,500+ papers** across the field
- Developed a taxonomy of **58 prompting techniques**
- Covered: prompt engineering, prompt hacking (attacks), and prompt optimization

### Key Findings
- Comprehensive vocabulary of 33 terms for the field
- Taxonomy of attack types: direct injection, indirect injection, jailbreaking
- Taxonomy of defenses: input filtering, output monitoring, fine-tuning
- Identified prompt injection as one of the most critical unsolved problems in LLM security

### Relevance to Your Project
- Provides the **broader academic context** for your related work section
- Useful for positioning your attack taxonomy within the larger landscape
- The defense categories they describe map to your Layer 1 (input filtering) and Layer 2 (output monitoring)

### How to Cite
> Schulhoff et al. (2024) provide the most comprehensive survey of prompting techniques to date, categorizing both attack and defense strategies. Their taxonomy of prompt injection defenses informs our layered defense architecture.

---

## Summary: How These Papers Map to Your Project

| Paper | What They Give You | How You Build On It |
|-------|-------------------|---------------------|
| Zhang et al. (2026) | Real-world prevalence data, detection methods | You measure attack SUCCESS and test DEFENSES |
| Schulhoff et al. (2023) | Attack taxonomy, competition methodology | You apply taxonomy to resume domain, measure ASR |
| Greshake et al. (2023) | Indirect injection framework | Your CV = untrusted data, your LLM = target application |
| Aminou et al. (2025) | Early resume-specific injection evidence | You extend with controlled experiments |
| Schulhoff et al. (2024) | Broader field context, defense taxonomy | You implement their defense categories (L1 + L2) |

---

## Your Unique Contribution Statement

> Existing work has established that prompt injection exists in resume screening (Zhang et al. 2026, Aminou et al. 2025) and provided taxonomies of general prompt injection attacks (Schulhoff et al. 2023, Greshake et al. 2023). However, no prior work has: (1) measured prompt injection attack success rates in controlled experiments with known ground truth, (2) compared injection resistance across multiple LLM architectures, (3) evaluated the effectiveness of layered defense architectures through ablation studies, or (4) compared the vulnerability of Direct prompting versus RAG pipelines in the hiring domain. Our work addresses these gaps.

---

*Document generated for research planning purposes. Read the full papers before citing in your final report.*
