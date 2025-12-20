# Product Requirements Document: Evaluation Dataset v2.0

**Document Version:** 1.0
**Date:** December 10, 2025
**Author:** Product Manager Agent
**Status:** Draft for Review
**Sprint:** 2-Week Sprint (Sprint 9)

---

## 📋 Executive Summary

SkillForge's current evaluation datasets consist of 41 synthetic examples (100% synthetic data) used to test the multi-agent LangGraph system. These datasets lack real-world complexity, edge cases, domain diversity, and difficulty stratification, limiting their effectiveness for validating production readiness.

This PRD defines requirements for **Evaluation Dataset v2.0**, which will introduce 70% real-world examples, comprehensive edge case coverage, difficulty tiers, adversarial testing, and expanded domain coverage (DevOps, Mobile, Data Engineering).

**Success Criteria:** Achieve 85% real-world data, cover 12+ domains, include 30+ edge cases, and establish quality gates for agent performance evaluation.

---

## 🎯 Problem Statement

### Current State Analysis

**Existing Datasets:**
- `agent_analysis_golden_v1.json` - 16 examples (8 agent types)
- `supervisor_golden_v1.json` - 20 examples (routing validation)
- `synthesis_golden_v1.json` - 5 examples (multi-agent synthesis)
- **Total:** 41 examples, 100% synthetic

**Identified Problems:**

1. **Zero Real-World Data**
   - All examples are hand-crafted synthetic scenarios
   - Does not reflect actual user content (messy, ambiguous, typo-ridden)
   - Overfits to idealized input patterns

2. **No Edge Case Coverage**
   - Missing ambiguous content (e.g., "Is React still worth learning?")
   - No conflicting information scenarios
   - No incomplete or malformed content
   - No adversarial examples (prompt injection, misleading claims)

3. **Lack of Difficulty Stratification**
   - No complexity labels (easy/medium/hard/expert)
   - Cannot measure agent performance across difficulty tiers
   - Impossible to set minimum competency thresholds per tier

4. **Limited Domain Diversity**
   - Overrepresents web development (React, Vue, FastAPI, Next.js)
   - Missing domains: DevOps, Mobile (iOS/Android), Data Engineering, ML Ops
   - No emerging tech coverage (WebAssembly, Deno 2.0, HTMX)

5. **No Adversarial Examples**
   - No outdated content (e.g., "Angular.js is the future")
   - No misleading benchmarks or claims
   - No security anti-patterns disguised as best practices

### Impact on System Quality

**Current Risks:**
- **Production Failures:** Agents may fail on real-world messy content
- **Blind Spots:** Missing edge cases lead to unhandled errors in production
- **Overconfidence:** 100% synthetic data inflates perceived accuracy
- **Incomplete Validation:** Cannot validate agent reasoning across difficulty levels

---

## 👥 User Stories

### Persona 1: ML Engineer (Quality Assurance)

**AS A** ML engineer responsible for agent quality,
**I WANT** a comprehensive evaluation dataset with real-world examples and edge cases,
**SO THAT** I can validate agent performance before production deployment and catch regressions during model upgrades.

**Acceptance Criteria:**
- Dataset includes 70%+ real-world examples from actual URLs
- Edge case coverage: ambiguous content, typos, conflicting info (30+ cases)
- Difficulty stratification: 4 tiers (easy/medium/hard/expert) with 25% distribution each
- Each example includes expected outputs with confidence thresholds
- Dataset enables A/B testing of different LLM models (GPT-4o Mini vs GPT-5 Mini)

**Success Metrics:**
- **Regression Detection Rate:** 95% - Catch 19 out of 20 regressions when agent logic changes
- **Model Comparison Time:** < 2 hours to run full evaluation on 2 models
- **False Positive Rate:** < 5% - Minimize spurious failures

---

### Persona 2: Backend Developer (Agent Development)

**AS A** backend developer implementing new agent capabilities,
**I WANT** domain-specific golden datasets with clear expected outputs,
**SO THAT** I can validate my agent logic during development without manual testing.

**Acceptance Criteria:**
- Domain-specific subsets: DevOps (15 examples), Mobile (15 examples), Data Eng (15 examples)
- Each example includes JSON schema for expected output structure
- Examples cover common failure modes (empty responses, hallucinations, off-topic routing)
- Dataset includes adversarial examples (outdated content, misleading claims)
- Clear documentation on how to add new examples

**Success Metrics:**
- **Dev Iteration Speed:** 30% faster - Reduce manual testing time per agent change
- **Domain Coverage:** 12+ domains covered (from current 5)
- **Adversarial Detection:** 90% - Agents correctly flag 9 out of 10 adversarial examples

---

### Persona 3: QA Engineer (Pre-Release Validation)

**AS A** QA engineer validating a release candidate,
**I WANT** automated evaluation reports with pass/fail thresholds,
**SO THAT** I can block releases that fail quality gates without manual review.

**Acceptance Criteria:**
- Automated evaluation script runs full dataset in < 10 minutes
- Pass/fail thresholds: Easy (85%), Medium (75%), Hard (65%), Expert (50%)
- Report includes per-agent accuracy, per-domain coverage, difficulty breakdowns
- CI integration: GitHub Actions workflow fails PR if quality gates not met
- Historical tracking: Compare current run to previous 5 runs

**Success Metrics:**
- **Release Confidence:** 95% - Block 95% of quality regressions before production
- **Evaluation Time:** < 10 minutes for full suite (140+ examples)
- **Threshold Clarity:** 100% - Zero ambiguity on pass/fail criteria

---

## 🎯 Goals & Success Metrics

### Primary Goals

**Goal 1: Real-World Data Coverage**
- **Metric:** % of real-world examples in dataset
- **Target:** 85% real-world (119 examples), 15% synthetic (21 examples)
- **Current:** 0% real-world (0 examples), 100% synthetic (41 examples)
- **Measurement:** Count examples sourced from actual URLs vs hand-crafted

**Goal 2: Edge Case Coverage**
- **Metric:** Number of edge case types covered
- **Target:** 8 edge case types × 5 examples each = 40 edge cases
- **Current:** 0 edge cases
- **Measurement:** Count examples tagged with edge case types (ambiguous, conflicting, incomplete, adversarial, outdated, malformed, off-topic, multilingual)

**Goal 3: Domain Diversity**
- **Metric:** Number of technical domains represented
- **Target:** 12 domains × 12 examples each = 144 examples (revised target: 140)
- **Current:** 5 domains (web dev focus)
- **Measurement:** Count unique domain tags (web dev, backend, DevOps, mobile, data eng, ML/AI, security, cloud, edge, embedded, blockchain, game dev)

**Goal 4: Difficulty Stratification**
- **Metric:** Even distribution across difficulty tiers
- **Target:** 4 tiers (easy: 35, medium: 35, hard: 35, expert: 35) = 140 examples
- **Current:** No difficulty labels
- **Measurement:** Count examples per difficulty tier

---

### Secondary Goals

**Goal 5: Adversarial Robustness**
- **Metric:** Number of adversarial examples
- **Target:** 25 adversarial examples (18% of dataset)
- **Current:** 0 adversarial examples
- **Measurement:** Count examples tagged as adversarial (outdated content, misleading benchmarks, security anti-patterns)

**Goal 6: Evaluation Velocity**
- **Metric:** Time to run full evaluation suite
- **Target:** < 10 minutes (GPT-5 Mini @ 200 req/min rate limit)
- **Current:** Unknown (no automated evaluation)
- **Measurement:** End-to-end time for 140 examples with parallelization

---

## 📊 MoSCoW Prioritization

### Must Have (Sprint 9 Deliverables)

**M1. Dataset Structure & Schema**
- JSON schema for agent analysis, supervisor routing, and synthesis golden sets
- Metadata fields: difficulty, domain, edge_case_type, data_source, date_added
- Version control: Dataset version in metadata.json

**M2. Real-World Data Collection**
- 70 real-world examples (50% of 140 target) from actual Langfuse runs
- Manual curation: Select diverse URLs analyzed in production/staging
- Quality review: Verify expected outputs match actual agent findings

**M3. Edge Case Coverage (Phase 1)**
- 20 edge cases covering 4 types: ambiguous, conflicting, incomplete, outdated
- Examples: "Is React still worth it?" (ambiguous), "Vue 3 vs Vue 2" (outdated), truncated articles (incomplete)

**M4. Domain Expansion**
- Add 3 new domains: DevOps (15), Mobile (15), Data Engineering (15) = 45 examples
- Ensure each domain has real-world examples (not all synthetic)

**M5. Difficulty Labels**
- Label all 140 examples with difficulty tier: easy, medium, hard, expert
- Distribution: 35 examples per tier (25% each)
- Difficulty criteria documented in DATASET_GUIDE.md

---

### Should Have (Sprint 9 Stretch Goals)

**S1. Automated Evaluation Script**
- Python script to run all 140 examples through LangGraph pipeline
- Output: JSON report with per-agent accuracy, per-domain coverage, difficulty breakdown
- Pass/fail thresholds: Easy (85%), Medium (75%), Hard (65%), Expert (50%)

**S2. Adversarial Examples**
- 15 adversarial examples: outdated content (5), misleading benchmarks (5), anti-patterns (5)
- Examples: "MongoDB is web scale" (misleading), "Storing passwords in plaintext is fine for dev" (anti-pattern)

**S3. CI Integration**
- GitHub Actions workflow: Run evaluation on PR merge to main
- PR comment with evaluation report (pass/fail, accuracy, regressions)

**S4. Historical Tracking**
- SQLite database to store evaluation results per commit/tag
- CLI tool to compare current run vs previous 5 runs
- Regression detection: Flag when accuracy drops >5% vs previous run

---

### Could Have (Future Sprints)

**C1. Multilingual Content**
- 10 examples with non-English content (Spanish, French, Chinese, Japanese)
- Test agents on code-switching content (e.g., English article with Spanish code comments)

**C2. Long-Form Content**
- 10 examples with 10,000+ word articles (vs typical 500-2000 words)
- Test chunking, summarization, and memory handling

**C3. Multimodal Content**
- 5 examples with images (architecture diagrams, code screenshots)
- Requires OCR or image-to-text preprocessing

**C4. Dynamic Benchmark**
- Auto-generate synthetic examples using LLM (inspired by Benchmark Self-Evolving pattern)
- Prevents overfitting to static dataset

---

### Won't Have (Out of Scope)

**W1. Video/Audio Transcripts**
- Reason: YouTube transcript extraction already handled, not evaluation bottleneck

**W2. GitHub Repository Analysis**
- Reason: Complex, requires code parsing, separate evaluation suite needed

**W3. User Interaction Logs**
- Reason: Privacy concerns, requires anonymization pipeline

**W4. Tutoring Session Evaluation**
- Reason: Separate PRD required for Socratic dialogue quality metrics

---

## ✅ Acceptance Criteria

### Dataset Quality Gates

**Criterion 1: Real-World Data Threshold**
- **Requirement:** ≥ 70% of examples sourced from actual URLs (98+ examples)
- **Validation:** Count examples with `data_source: "real_world"` vs `data_source: "synthetic"`
- **Blocker:** Dataset rejected if < 70% real-world

**Criterion 2: Domain Distribution**
- **Requirement:** All 12 domains have ≥ 10 examples each
- **Validation:** Count examples per domain tag
- **Blocker:** Dataset rejected if any domain has < 10 examples

**Criterion 3: Difficulty Balance**
- **Requirement:** Each difficulty tier (easy/medium/hard/expert) has 25% ± 5% of examples
- **Validation:** Distribution: Easy (30-40%), Medium (30-40%), Hard (30-40%), Expert (30-40%)
- **Blocker:** Dataset rejected if any tier < 20% or > 45%

**Criterion 4: Edge Case Coverage**
- **Requirement:** ≥ 20 edge case examples covering ≥ 4 edge case types
- **Validation:** Count examples with `edge_case_type` != null
- **Blocker:** Dataset rejected if < 20 edge cases

**Criterion 5: Expected Output Quality**
- **Requirement:** 100% of examples have expected outputs matching JSON schema
- **Validation:** JSON schema validation passes for all examples
- **Blocker:** Dataset rejected if any example fails schema validation

---

### Evaluation Pipeline Acceptance

**Criterion 6: Evaluation Speed**
- **Requirement:** Full evaluation (140 examples) completes in < 10 minutes
- **Validation:** Measure end-to-end time with parallelization (10 workers)
- **Blocker:** Pipeline rejected if > 10 minutes (indicates rate limiting issues)

**Criterion 7: Pass/Fail Thresholds**
- **Requirement:** Agents meet minimum accuracy per difficulty tier: Easy (85%), Medium (75%), Hard (65%), Expert (50%)
- **Validation:** Run evaluation on current production agents
- **Blocker:** Release blocked if any tier fails threshold

**Criterion 8: Regression Detection**
- **Requirement:** Evaluation detects ≥ 95% of known regressions (based on synthetic regression dataset)
- **Validation:** Introduce 20 synthetic bugs, measure detection rate
- **Blocker:** Pipeline rejected if detection rate < 95%

---

### Documentation Acceptance

**Criterion 9: Dataset Guide**
- **Requirement:** DATASET_GUIDE.md includes: schema definition, example format, difficulty criteria, domain taxonomy, edge case types, how to add examples
- **Validation:** Manual review by 2 engineers
- **Blocker:** Documentation rejected if missing any required section

**Criterion 10: Evaluation README**
- **Requirement:** README includes: how to run evaluation, interpreting results, pass/fail thresholds, CI integration guide, troubleshooting
- **Validation:** New engineer can run evaluation without help in < 10 minutes
- **Blocker:** Documentation rejected if onboarding time > 10 minutes

---

## 🚨 Risk Assessment

### High Risks (Probability × Impact = Severity)

**Risk 1: Real-World Data Quality (Probability: 60%, Impact: High, Severity: HIGH)**
- **Description:** Real-world examples may have incorrect expected outputs due to manual curation errors
- **Mitigation:**
  1. Two-person review: One person creates, another verifies expected outputs
  2. Run evaluation on staging agents first, inspect failures
  3. Use Langfuse traces to validate expected outputs match actual runs
- **Contingency:** If >10% of examples have wrong expected outputs, revert to 50% real-world target (70 examples)

**Risk 2: Evaluation Time Exceeds Budget (Probability: 40%, Impact: Medium, Severity: MEDIUM)**
- **Description:** 140 examples × 8 agents = 1,120 LLM calls may exceed 10-minute target with GPT-5 Mini rate limits (200 req/min)
- **Mitigation:**
  1. Use caching: Cache supervisor routing decisions (shared across examples)
  2. Parallelization: Run 10 examples concurrently (respects 200 req/min limit)
  3. Model selection: Use GPT-4o Mini (400 req/min) for evaluation
- **Contingency:** If evaluation time > 10 minutes, reduce dataset to 100 examples (priority: edge cases > domains)

**Risk 3: Difficulty Labeling Inconsistency (Probability: 50%, Impact: Medium, Severity: MEDIUM)**
- **Description:** Subjective difficulty labels may be inconsistent across curators (one person's "hard" is another's "medium")
- **Mitigation:**
  1. Define objective criteria: Easy (1-2 agents, <500 words), Medium (3-4 agents, 500-1500 words), Hard (5-6 agents, 1500-3000 words), Expert (7-8 agents, >3000 words)
  2. Calibration session: 5 engineers label 10 examples, discuss discrepancies
  3. Re-label after calibration
- **Contingency:** If >20% disagreement after calibration, use agent count + word count as proxy for difficulty (automated labeling)

---

### Medium Risks

**Risk 4: Adversarial Examples Too Obvious (Probability: 30%, Impact: Low, Severity: LOW)**
- **Description:** Agents may easily detect adversarial examples if they're too blatant (e.g., "PHP is the best language ever")
- **Mitigation:** Use subtle adversarial examples (e.g., outdated content from 2020 presented as 2025 best practices)
- **Contingency:** If agents detect 100% of adversarial examples, add more nuanced cases

**Risk 5: Domain Expertise Gaps (Probability: 40%, Impact: Low, Severity: LOW)**
- **Description:** Team may lack expertise in domains like Mobile, Data Engineering to create quality examples
- **Mitigation:** Recruit domain experts for review, use real-world examples from public sources (Medium, Dev.to)
- **Contingency:** If domain quality is low, focus on web dev, backend, DevOps (team strengths)

---

### Low Risks

**Risk 6: Dataset Drift Over Time (Probability: 20%, Impact: Low, Severity: LOW)**
- **Description:** Dataset becomes outdated as technology evolves (e.g., React 19 examples irrelevant when React 20 releases)
- **Mitigation:** Annual dataset refresh policy, version tagging (v2.0, v2.1, v3.0)
- **Contingency:** Add "last_validated" metadata field, flag stale examples (>12 months)

---

## 📦 Deliverables (2-Week Sprint)

### Week 1: Foundation & Data Collection

**Day 1-2: Schema & Structure**
- [ ] Define JSON schema for agent analysis, supervisor routing, synthesis datasets
- [ ] Create metadata.json with dataset version, creation date, statistics
- [ ] Create DATASET_GUIDE.md with schema, criteria, taxonomy

**Day 3-5: Real-World Data Collection (Must Have)**
- [ ] Query Langfuse for 100 most diverse production/staging analyses
- [ ] Select 70 examples across domains: web dev (20), backend (15), DevOps (15), mobile (10), data eng (10)
- [ ] Manual curation: Extract content, verify expected outputs, add metadata

**Day 5-7: Edge Cases & Adversarial Examples (Must Have + Should Have)**
- [ ] Create 20 edge case examples: ambiguous (5), conflicting (5), incomplete (5), outdated (5)
- [ ] Create 15 adversarial examples: misleading benchmarks (5), anti-patterns (5), outdated content (5)
- [ ] Add difficulty labels to all 105 examples (70 real-world + 20 edge + 15 adversarial)

---

### Week 2: Evaluation Pipeline & Validation

**Day 8-10: Domain Expansion (Must Have)**
- [ ] Add 35 synthetic examples to reach 140 total: DevOps (5 more), mobile (5 more), data eng (5 more), emerging tech (10), security (10)
- [ ] Verify domain distribution: 12 domains × 10-15 examples each
- [ ] Verify difficulty distribution: 35 examples per tier (easy/medium/hard/expert)

**Day 11-12: Automated Evaluation Script (Should Have)**
- [ ] Python script: `evaluate_agents.py --dataset=v2.0 --model=gpt-5-mini`
- [ ] Output: JSON report with per-agent accuracy, per-domain coverage, difficulty breakdown
- [ ] Pass/fail thresholds: Easy (85%), Medium (75%), Hard (65%), Expert (50%)

**Day 13-14: Validation & Documentation**
- [ ] Run evaluation on staging agents, verify pass/fail logic
- [ ] Create regression dataset: 20 synthetic bugs to test detection rate
- [ ] Write README: How to run evaluation, interpret results, CI integration
- [ ] Two-person review: One engineer creates, another verifies 20 random examples

---

## 📈 Success Metrics (Post-Deployment)

### Quality Metrics (Week 1 Post-Launch)

**Metric 1: Real-World Data %**
- **Target:** 85% real-world (119 examples)
- **Actual:** _[To be measured]_
- **Pass/Fail:** Pass if ≥ 70% (98+ examples)

**Metric 2: Domain Coverage**
- **Target:** 12 domains × 10+ examples each
- **Actual:** _[To be measured]_
- **Pass/Fail:** Pass if all 12 domains have ≥ 10 examples

**Metric 3: Edge Case Coverage**
- **Target:** 40 edge cases (8 types × 5 examples)
- **Actual:** _[To be measured]_
- **Pass/Fail:** Pass if ≥ 20 edge cases

---

### Performance Metrics (Week 2 Post-Launch)

**Metric 4: Agent Accuracy (Per Difficulty Tier)**
- **Target:** Easy (85%), Medium (75%), Hard (65%), Expert (50%)
- **Actual:** _[Run evaluation to measure]_
- **Pass/Fail:** Pass if all tiers meet minimum thresholds

**Metric 5: Regression Detection Rate**
- **Target:** 95% (19 out of 20 known regressions detected)
- **Actual:** _[Introduce synthetic bugs and measure]_
- **Pass/Fail:** Pass if ≥ 95% detection

**Metric 6: Evaluation Time**
- **Target:** < 10 minutes for full suite (140 examples)
- **Actual:** _[Measure end-to-end time]_
- **Pass/Fail:** Pass if < 10 minutes

---

### Adoption Metrics (Month 1 Post-Launch)

**Metric 7: CI Integration Usage**
- **Target:** 80% of PRs run evaluation automatically
- **Actual:** _[Track GitHub Actions runs]_
- **Pass/Fail:** Pass if ≥ 80% adoption

**Metric 8: Developer Iteration Speed**
- **Target:** 30% reduction in manual testing time per agent change
- **Actual:** _[Survey developers]_
- **Pass/Fail:** Pass if ≥ 20% time savings

---

## 📋 Appendix

### A. Difficulty Tier Criteria

| Tier   | Agents Required | Word Count | Characteristics |
|--------|----------------|------------|-----------------|
| Easy   | 1-2 agents     | < 500      | Single domain, clear recommendation |
| Medium | 3-4 agents     | 500-1500   | Multi-domain, balanced pros/cons |
| Hard   | 5-6 agents     | 1500-3000  | Complex trade-offs, integration considerations |
| Expert | 7-8 agents     | > 3000     | Architecture decisions, cross-domain synthesis |

### B. Domain Taxonomy

1. **Web Development** - React, Vue, Angular, Svelte, HTML/CSS, frontend frameworks
2. **Backend** - FastAPI, Django, Node.js, Go, REST APIs, GraphQL
3. **DevOps** - Docker, Kubernetes, CI/CD, Infrastructure as Code, monitoring
4. **Mobile** - React Native, Flutter, iOS, Android, mobile architecture
5. **Data Engineering** - ETL, data pipelines, Spark, Airflow, data warehousing
6. **Machine Learning/AI** - LLMs, RAG, embeddings, LangChain, PyTorch
7. **Security** - Authentication, authorization, OWASP, encryption, vulnerabilities
8. **Cloud** - AWS, Azure, GCP, serverless, cloud architecture
9. **Edge Computing** - Cloudflare Workers, Deno Deploy, edge functions
10. **Embedded** - IoT, microcontrollers, real-time systems
11. **Blockchain** - Smart contracts, Web3, distributed systems
12. **Game Development** - Unity, Unreal, game engines, graphics

### C. Edge Case Types

1. **Ambiguous** - Content that could be routed to multiple agents (e.g., "Is React worth it?")
2. **Conflicting** - Content with contradictory information (e.g., benchmarks showing different winners)
3. **Incomplete** - Truncated articles, missing context, broken examples
4. **Outdated** - Old content presented as current (e.g., "Angular.js is the future")
5. **Adversarial** - Misleading claims, anti-patterns disguised as best practices
6. **Malformed** - Broken HTML, encoding issues, missing metadata
7. **Off-Topic** - Non-technical content (e.g., opinion pieces, politics)
8. **Multilingual** - Non-English content, code-switching

### D. Evaluation Report Schema

```json
{
  "version": "2.0",
  "timestamp": "2025-12-10T14:30:00Z",
  "model": "gpt-5-mini",
  "total_examples": 140,
  "accuracy": {
    "overall": 0.78,
    "by_difficulty": {
      "easy": 0.88,
      "medium": 0.79,
      "hard": 0.68,
      "expert": 0.53
    },
    "by_domain": {
      "web_dev": 0.85,
      "backend": 0.82,
      "devops": 0.71,
      "mobile": 0.68,
      "data_eng": 0.74
    },
    "by_agent": {
      "tech_comparator": 0.82,
      "security_auditor": 0.91,
      "implementation_planner": 0.75
    }
  },
  "pass_fail": {
    "easy": "PASS",
    "medium": "PASS",
    "hard": "PASS",
    "expert": "PASS"
  },
  "regressions_detected": 18,
  "execution_time_seconds": 543
}
```

---

## 🔗 Related Documents

- **Current Datasets:**
  - `/backend/app/evaluation/datasets/agent_analysis_golden_v1.json` (16 examples)
  - `/backend/app/evaluation/datasets/supervisor_golden_v1.json` (20 examples)
  - `/backend/app/evaluation/datasets/synthesis_golden_v1.json` (5 examples)

- **Documentation:**
  - `docs/ROADMAP.md` - System architecture and agent descriptions
  - `docs/ARCHITECTURE.md` - LangGraph workflow details
  - `.claude/context/shared-context.json` - Recent architectural decisions

- **Future PRDs:**
  - Tutoring Session Evaluation (Socratic dialogue quality metrics)
  - Dynamic Benchmark Generation (Self-evolving evaluation dataset)

---

**Document Status:** Ready for Review
**Approval Required From:** Engineering Lead, QA Lead, ML Engineer
**Next Steps:** Review PRD → Approve → Create Sprint 9 GitHub Issues → Begin Week 1 Implementation
