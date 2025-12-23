# 📊 Product Metrics Research - Executive Summary

**Date:** December 22, 2025  
**Status:** Research Complete ✅  
**Full Analysis:** See `docs/PRODUCT_METRICS_ANALYSIS.md`

---

## ✅ Current State Correction (Dec 22, 2025)

**FEEDBACK SYSTEM ALREADY EXISTS!**

### What We Have ✅
- ✅ Thumbs up/down buttons (`FeedbackButtons` component)
- ✅ Feedback submission API (`POST /api/v1/annotations/feedback`)
- ✅ Langfuse integration (feedback submitted as scores)
- ✅ Annotation queue system (for low-quality artifacts)
- ✅ E2E tests for feedback flow

### What's Missing ⚠️
- ⚠️ Feedback not stored in database (only in Langfuse - hard to aggregate)
- ⚠️ No user_id on feedback (anonymous until auth)
- ❌ No retention/churn tracking (requires user_id)

---

## 🎯 Key Findings

### 1. Two-Layer Metrics Architecture Required

**Product Signals Layer:** Track user behavior (churn, retention, activation)
- **Current State:** ⚠️ Foundation exists but requires auth (#421)
- **Critical Gap:** No `user_id` in analyses/tutoring_sessions tables

**Response Quality Layer:** Track artifact/tutoring quality (task success, user feedback)
- **Current State:** ✅ G-Eval scores exist in Langfuse
- **Critical Gap:** No user-facing feedback collection (thumbs up/down)

---

### 2. SkillForge-Specific Metric Definitions

Unlike ChatGPT (daily chat), SkillForge users have **periodic deep-dive sessions** (weekly/monthly):

| Metric | ChatGPT Definition | SkillForge Definition |
|--------|-------------------|----------------------|
| **Activation** | 3+ messages in first session | First analysis + artifact download |
| **Retention** | Daily active users | Weekly/monthly active users |
| **DAU/MAU** | 0.4-0.6 (daily use) | 0.1-0.3 (weekly use) - **Lower is normal** |
| **Session Length** | Messages per session | Time from analysis start → artifact download |
| **Churn** | 30-day inactive (no sessions) | 30-day inactive (no analyses/downloads) |

---

### 3. Critical Integration Points

**Already Implemented ✅:**
- Artifact `download_count` tracking
- Analysis status/error tracking
- Tutoring session completion tracking
- Langfuse observability (G-Eval scores)

**Missing Implementation ❌:**
- User-level tracking (requires auth - Issue #421)
- User feedback collection (thumbs up/down, ratings)
- Retention/churn calculations
- Cohort analysis

---

## 🚨 Immediate Blockers

### Blocker #1: Authentication (Issue #421)
**Impact:** Cannot track user-level metrics without `user_id`

**Required For:**
- Activation rate (first analysis per user)
- Retention cohorts (Week 1/4/12)
- Churn rate calculations
- User-level engagement metrics

**Action:** Complete Issue #421 before implementing Phase 1 metrics

---

### Blocker #2: Feedback Analytics Aggregation
**Impact:** Feedback exists but hard to aggregate (only in Langfuse, not in database)

**Current State:**
- ✅ User feedback UI exists (thumbs up/down buttons)
- ✅ Feedback submission API exists (POST /api/v1/annotations/feedback)
- ✅ Feedback submitted to Langfuse as scores
- ⚠️ Feedback NOT stored in database (hard to aggregate)
- ⚠️ No user_id on feedback (anonymous until auth)

**Required For:**
- Artifact quality rating aggregation
- Feedback trend analysis
- Calibration analysis (G-Eval vs user ratings)
- Quality metrics dashboard

**Action:** Choose Option A (store in DB) or Option B (query Langfuse API) after auth is complete

---

## 📋 Implementation Phases

### Phase 1: Foundation (After Auth #421)
**Effort:** 1-2 days  
**Enables:** User-level tracking, activation, retention, churn

**Tasks:**
1. Add `user_id` to `analyses` table (migration)
2. Add `user_id` to `tutoring_sessions` table (migration)
3. Update repositories to store user_id

---

### Phase 2: User Feedback Collection
**Effort:** 3-5 days  
**Enables:** Response quality metrics, user satisfaction tracking

**Tasks:**
1. Create `artifact_feedback` table
2. Create `POST /api/v1/artifacts/{id}/feedback` endpoint
3. Add feedback UI (thumbs up/down buttons)
4. Create `tutoring_session_feedback` table

---

### Phase 3: Retention & Cohort Analysis
**Effort:** 5-7 days  
**Enables:** Retention curves, cohort comparisons, churn trends

**Tasks:**
1. Create analytics service (retention, churn, activation)
2. Create analytics dashboard API endpoints
3. Build frontend dashboard (optional)

---

### Phase 4: Quality Metrics Aggregation
**Effort:** 4-6 days  
**Enables:** Quality trend analysis, calibration, error severity

**Tasks:**
1. Aggregate user ratings by artifact
2. Compare G-Eval vs user ratings (calibration)
3. Create quality dashboard API

---

## 🎯 Recommended Metrics Dashboard (MVP)

### Product Signals
- **Activation Rate:** % users who download first artifact
- **Retention:** Week 1/4/12 % still active
- **Engagement:** Analyses per user per month
- **Churn Rate:** % users inactive >30 days

### Response Quality
- **Artifact Quality:** Avg user rating (1-5 stars)
- **Tutoring Quality:** Completion rate, satisfaction score
- **Analysis Success:** % completed (vs failed)
- **Calibration:** G-Eval vs user rating correlation

---

## 🔗 Alignment with Current Roadmap

**Current Milestone:** 🟤 Triple-Consumer Artifacts (#299-304)
- ✅ Artifact quality gates exist
- ⚠️ Missing: User feedback collection (Phase 2)

**Next Milestone:** 🟡 Tutoring System
- ✅ TutoringSession model exists
- ⚠️ Missing: User satisfaction feedback

**Upcoming:** 🔵 Staging/Production
- 🚨 **BLOCKER:** Auth (#421) required before user-level metrics

---

## ✅ Validation: December 22, 2025

**Research Sources:** ✅ Validated (2025 LLM product metrics best practices)  
**Codebase Analysis:** ✅ Complete (database models, API endpoints, observability)  
**Integration Feasibility:** ✅ Confirmed (existing infrastructure supports metrics)  
**Roadmap Alignment:** ✅ Aligned (phases match current priorities)

**Conclusion:** ✅ **Ready for implementation planning**

---

## 📚 Next Steps

1. **Review Full Analysis:** Read `docs/PRODUCT_METRICS_ANALYSIS.md` for detailed architecture
2. **Prioritize Auth:** Ensure Issue #421 (#422) completed before Phase 1 metrics
3. **Plan Phase 2:** Design feedback UI components (thumbs up/down buttons)
4. **Create GitHub Issues:** Break down phases into implementable tasks

---

**Document Version:** 1.0  
**Last Updated:** December 22, 2025
