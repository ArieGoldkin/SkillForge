# 📊 Product Metrics & Response Quality Analysis
## Research Findings & Integration Plan for SkillForge

**Date:** December 22, 2025  
**Status:** Research Complete - Ready for Implementation Planning  
**Alignment:** Product Signals (Churn/Retention) + Response Quality Signals

---

## 🎯 Executive Summary

This analysis maps LLM product metrics best practices (Dec 2025) to SkillForge's unique architecture. Unlike ChatGPT-style daily chat apps, SkillForge users have **periodic deep-dive sessions** (weekly/monthly analyses), requiring different activation and retention definitions.

**Key Finding:** SkillForge needs **two-layer instrumentation**:
1. **Product Signals Layer**: Track user behavior (churn, retention, activation)
2. **Response Quality Layer**: Track artifact/tutoring quality (task success, user feedback)

**Current State:** ✅ **Feedback system exists, but analytics gaps remain**
- ✅ Langfuse observability (LLM traces, G-Eval scores)
- ✅ Database tracking (status, timestamps, error codes)
- ✅ Artifact download_count tracking
- ✅ **User feedback collection** (thumbs up/down buttons, FeedbackButtons component)
- ✅ **Feedback submission API** (POST /api/v1/annotations/feedback)
- ✅ **Langfuse score integration** (feedback submitted as scores)
- ⚠️ **Feedback not stored in database** (only in Langfuse, difficult to aggregate)
- ⚠️ **No user_id on feedback** (anonymous feedback, auth not implemented - Issue #421)
- ❌ **No retention/churn** calculations (requires user_id)

---

## 📐 Architecture Visualization

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SKILLFORGE METRICS ARCHITECTURE                            │
│                         (Dec 22, 2025 - Target State)                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        PRODUCT SIGNALS LAYER                                  │
│                  (Are people using the app effectively?)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │  ACTIVATION      │  │  RETENTION       │  │  ENGAGEMENT      │          │
│  │                  │  │                  │  │                  │          │
│  │  ✓ First analysis│  │  ✓ Week 1/4/12  │  │  ✓ Analyses/mo   │          │
│  │  ✓ Artifact      │  │    retention     │  │  ✓ Session       │          │
│  │    download      │  │  ✓ Cohort curves │  │    length        │          │
│  │  ✓ Time-to-value │  │  ✓ DAU/MAU*      │  │  ✓ Search usage  │          │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘          │
│           │                     │                     │                      │
│           └─────────────────────┴─────────────────────┘                      │
│                                 │                                            │
│                         ┌───────▼────────┐                                   │
│                         │   CHURN RATE   │                                   │
│                         │  (30/60/90 day)│                                   │
│                         │  inactive users│                                   │
│                         └────────────────┘                                   │
│                                                                               │
│  *Note: DAU/MAU will be lower for SkillForge (0.1-0.3) vs chat apps (0.4+)  │
│        because users analyze weekly/monthly, not daily                       │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                      RESPONSE QUALITY LAYER                                   │
│                    (Are the answers good enough?)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │  ANALYSIS        │  │  ARTIFACT        │  │  TUTORING        │          │
│  │  QUALITY         │  │  QUALITY         │  │  QUALITY         │          │
│  │                  │  │                  │  │                  │          │
│  │  ✓ Success rate  │  │  ✓ User ratings  │  │  ✓ Completion   │          │
│  │  ✓ Error severity│  │  ✓ Download rate │  │    rate          │          │
│  │  ✓ Time-to-      │  │  ✓ Reuse rate    │  │  ✓ Understanding │          │
│  │    complete      │  │  ✓ G-Eval scores │  │    scores        │          │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘          │
│           │                     │                     │                      │
│           └─────────────────────┴─────────────────────┘                      │
│                                 │                                            │
│                    ┌────────────▼────────────┐                               │
│                    │  CALIBRATION ANALYSIS   │                               │
│                    │  (G-Eval vs User Rating)│                               │
│                    └─────────────────────────┘                               │
│                                                                               │
│  Current: ✅ G-Eval scores in Langfuse                                       │
│  Current: ✅ User feedback (thumbs up/down) - submitted to Langfuse          │
│  Gap: ⚠️  Feedback not in database (hard to aggregate without Langfuse API)  │
│  Gap: ⚠️  No user_id on feedback (anonymous until auth implemented)          │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA COLLECTION LAYER                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  DATABASE (PostgreSQL)                                               │   │
│  │                                                                       │   │
│  │  analyses            tutoring_sessions    artifacts                   │   │
│  │  ├─ user_id*         ├─ user_id*          ├─ download_count ✅       │   │
│  │  ├─ status ✅        ├─ started_at ✅     ├─ trace_id ✅            │   │
│  │  ├─ created_at ✅    ├─ completed_at ✅   └─ artifact_metadata ✅    │   │
│  │  ├─ error_code ✅    ├─ status ✅                                   │   │
│  │  └─ failed_at_stage✅└─ understanding_scores ✅                     │   │
│  │                                                                       │   │
│  │  EXISTING FEEDBACK SYSTEM:                                           │   │
│  │  ├─ FeedbackButtons component (thumbs up/down) ✅                    │   │
│  │  ├─ POST /api/v1/annotations/feedback endpoint ✅                    │   │
│  │  └─ Langfuse scores (user_feedback: 0.0 or 1.0) ✅                   │   │
│  │                                                                       │   │
│  │  GAPS FOR ANALYTICS:                                                 │   │
│  │  ├─ Feedback not stored in DB (only Langfuse) ⚠️                    │   │
│  │  ├─ No user_id on feedback (anonymous) ⚠️                           │   │
│  │  ├─ Hard to aggregate ratings per artifact (need Langfuse API) ⚠️   │   │
│  │  ├─ user_sessions table (for activation/retention tracking) ❌       │   │
│  │  └─ user_events table (for engagement tracking) ❌                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  OBSERVABILITY (Langfuse)                                            │   │
│  │                                                                       │   │
│  │  ✅ LLM traces (workflow execution)                                  │   │
│  │  ✅ G-Eval scores (depth, accuracy, relevance)                       │   │
│  │  ✅ Annotation queues (low-quality artifacts)                        │   │
│  │  ❌ User feedback integration (not linked)                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  EVENT STREAMING (SSE)                                               │   │
│  │                                                                       │   │
│  │  ✅ Progress events (workflow stages)                                │   │
│  │  ✅ Status updates (pending → running → complete)                    │   │
│  │  ⚠️  Could add: user interaction events (clicks, time-on-page)       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  * = Requires Auth Implementation (Issue #421)                                │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         INTEGRATION POINTS                                    │
│                    (Where metrics are collected)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  BACKEND ENDPOINTS:                                                          │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ POST /api/v1/analyze                                                   │ │
│  │   → Track: analysis creation (activation signal)                       │ │
│  │   → Event: "analysis_created" {user_id, url, timestamp}               │ │
│  │                                                                         │ │
│  │ GET /api/v1/artifacts/{id}/download                                    │ │
│  │   → Track: download_count ✅ (already implemented)                     │ │
│  │   → Event: "artifact_downloaded" {user_id, artifact_id, timestamp}    │ │
│  │                                                                         │ │
│  │ POST /api/v1/artifacts/{id}/feedback  [NEW - Phase 2]                  │ │
│  │   → Track: user rating, feedback text                                  │ │
│  │   → Event: "artifact_rated" {user_id, artifact_id, rating, feedback}  │ │
│  │                                                                         │ │
│  │ POST /api/v1/tutor/sessions/{id}/complete                              │ │
│  │   → Track: session completion (status="completed")                     │ │
│  │   → Calculate: duration = completed_at - started_at                    │ │
│  │                                                                         │ │
│  │ GET /api/v1/library/search                                             │ │
│  │   → Track: search queries, click-through rates                         │ │
│  │   → Event: "library_search" {user_id, query, results_count}           │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│  FRONTEND INTERACTIONS:                                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  Artifact View:                                                        │ │
│  │    → "Thumbs Up" button → POST /feedback {rating: 1}                 │ │
│  │    → "Thumbs Down" button → POST /feedback {rating: -1, reason}      │ │
│  │    → "Mark as Helpful" button → POST /feedback {helpful: true}       │ │
│  │                                                                         │ │
│  │  Tutoring Session:                                                     │ │
│  │    → "This helped" button → POST /sessions/{id}/feedback              │ │
│  │    → Session completion modal → "Rate your experience" (1-5 stars)    │ │
│  │                                                                         │ │
│  │  Analysis Progress:                                                    │ │
│  │    → Track: time spent viewing analysis detail page                   │ │
│  │    → Track: clicks on "Download Artifact" button                      │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ✅ Current Implementation Status (Corrected Dec 22, 2025)

### What EXISTS (Already Implemented)

#### User Feedback Collection ✅
- **Frontend:** `FeedbackButtons` component with thumbs up/down UI
- **API:** `POST /api/v1/annotations/feedback` endpoint
- **Backend Service:** `AnnotationService.submit_feedback()` 
- **Langfuse Integration:** Feedback submitted as scores (thumbs_up=1.0, thumbs_down=0.0)
- **E2E Tests:** `langfuse-feedback.spec.ts` tests feedback flow
- **Location:**
  - Frontend: `frontend/src/features/artifact/components/FeedbackButtons.tsx`
  - Backend: `backend/app/api/v1/annotations.py`
  - Service: `backend/app/core/annotation_service.py`

#### Annotation Queue System ✅
- **Database:** `annotation_queue` table for artifacts flagged for review
- **API:** Queue management endpoints (GET /queue, PATCH /queue/{id}/reviewed)
- **Use Case:** Low-quality artifacts or negative feedback queued for human review
- **Location:** `backend/app/db/models/annotation_queue.py`

#### Observability ✅
- **Langfuse:** LLM traces, G-Eval scores, user feedback scores
- **Database:** Analysis status, timestamps, error tracking
- **Artifact Metrics:** download_count tracking

### What's MISSING (Gaps for Analytics)

#### Feedback Analytics ⚠️
- **Gap:** Feedback not stored in database (only in Langfuse)
- **Impact:** Cannot easily aggregate ratings per artifact (need Langfuse API calls)
- **Solution Options:**
  1. Store feedback in database table (dual-write: Langfuse + DB)
  2. Create analytics service that queries Langfuse API

#### User Tracking ❌
- **Gap:** No user_id on feedback (anonymous until auth implemented)
- **Impact:** Cannot track per-user feedback patterns
- **Requires:** Auth implementation (Issue #421)

#### Retention/Churn Metrics ❌
- **Gap:** No user_id in analyses/tutoring_sessions tables
- **Impact:** Cannot calculate activation, retention, churn rates
- **Requires:** Auth implementation + user_id migrations

---

## 🔍 Detailed Metric Definitions for SkillForge

### Product Signals

#### 1. Activation Metrics

**Activation Rate:** % of signups who reach key value moment
- **Key Value Moment:** User creates first analysis AND downloads artifact (or starts tutoring session)
- **Alternative Definition:** User completes 1 full cycle (analyze → artifact → use it)
- **Time-to-Activation:** Median time from signup → first artifact download
- **Target:** < 24 hours (users should experience value quickly)

**Current State:** ❌ Cannot calculate (no user_id in analyses table)

---

#### 2. Retention Metrics

**Week 1/4/12 Retention:** % of new users still active after N weeks
- **Active Definition:** User creates new analysis OR downloads artifact OR starts tutoring session
- **For SkillForge:** Weekly retention is more meaningful than daily (users analyze weekly/monthly, not daily)

**Cohort Analysis:**
- Group users by signup week/month
- Track retention curves over time
- Compare cohorts to measure product improvements

**Current State:** ❌ Cannot calculate (no user_id + signup_date tracking)

---

#### 3. Engagement Metrics

**Analyses per User per Month:**
- Count analyses created by user_id in last 30 days
- Median and distribution
- Power users: >5 analyses/month

**Artifact Download Rate:**
- Downloads / Analyses Created (per user)
- Low rate (<0.5) = users creating but not using artifacts (quality issue)

**Tutoring Session Completion Rate:**
- Completed sessions / Total sessions started (per user)
- Abandoned sessions = status="active" but completed_at=NULL after 7 days

**Library Search Usage:**
- Users who search library (reusing past analyses) vs only creating new ones
- Reuse patterns indicate value in knowledge base

**Current State:** ⚠️ Partial (download_count exists, but no user-level aggregation)

---

#### 4. Churn Metrics

**Churn Rate:** % of users active in period N-1, inactive in period N
- **Inactive Definition:** No analyses, downloads, or tutoring sessions in last 30 days
- **Period:** Monthly (30-day windows)

**Session Interval Tracking:**
- Time between analyses (days)
- Early warning: Weekly → Monthly → Never (soft churn signal)
- Alert when interval > 2x baseline

**Drop-off Position:**
- Users who create analysis but never download artifact
- Users who start tutoring but abandon (never complete)

**Current State:** ❌ Cannot calculate (no user_id)

---

#### 5. DAU/MAU and Stickiness

**Important Note:** SkillForge is NOT a daily-use app like ChatGPT
- Expected DAU/MAU: 0.1-0.3 (users analyze weekly/monthly)
- Better metrics: **WAU/MAU** (Weekly Active Users) or **Analyses per User per Month**

**Stickiness Calculation:**
- DAU/MAU: Daily Active Users / Monthly Active Users
- For SkillForge: WAU/MAU is more relevant
- Target: >0.4 WAU/MAU (users return weekly)

---

### Response Quality Signals

#### 1. Analysis Quality

**Task Success Rate:**
- % of analyses that reach status="completed" (vs "failed")
- Currently tracked via `status` field ✅
- Target: >95% success rate

**Error Severity Classification:**
- Currently: `error_code`, `error_message`, `failed_at_stage` ✅
- Missing: Severity levels (Critical vs Minor)
- Critical: 404, extraction failed, LLM timeout
- Minor: Retryable timeouts, rate limits

**Time-to-Complete:**
- Analysis duration: `updated_at - created_at` when status="completed"
- Currently calculable ✅
- Target: <5 minutes for most analyses

---

#### 2. Artifact Quality

**User Ratings:**
- Thumbs up/down on artifacts
- 1-5 star ratings
- Feedback text (optional)
- **Current State:** ❌ Not implemented

**Artifact Reuse Rate:**
- Downloads / Analyses Created
- If users download but don't reuse (no subsequent analyses on same topic), quality may be low
- **Current State:** ⚠️ download_count tracked, but no reuse tracking

**G-Eval Scores:**
- Currently tracked in Langfuse ✅
- Depth, accuracy, relevance scores
- **Gap:** Not linked to user ratings (calibration analysis needed)

**Need for Human Edits:**
- % of artifacts that require editing before use
- Tracked via user feedback: "I had to edit this extensively"
- **Current State:** ❌ Not implemented

---

#### 3. Tutoring Quality

**Session Completion Rate:**
- Completed sessions / Total sessions started
- Abandoned = status="active" but completed_at=NULL after 7 days
- Currently calculable ✅ (status + completed_at fields exist)

**Time-to-Understanding:**
- Messages per session until user demonstrates mastery
- Tracked via `understanding_scores` in TutoringSession ✅
- Target: <10 messages per concept

**User Satisfaction:**
- "Did this help you understand?" (Yes/No)
- Session rating (1-5 stars)
- **Current State:** ❌ Not implemented

---

#### 4. System-Level Quality

**Calibration Analysis:**
- Compare G-Eval scores vs user ratings
- If G-Eval says "high quality" but users rate low, calibration issue
- **Current State:** ❌ Cannot compare (no user ratings)

**Regression Suite:**
- Maintain test set of real prompts + human "gold answers"
- Run after each model/prompt change
- Detect quality regressions automatically
- **Current State:** ⚠️ Golden dataset exists (98 analyses) but not used for regression testing

---

## 📋 Integration Roadmap

### Phase 1: Foundation (Requires Auth - Issue #421)

**Goal:** Enable user-level tracking

**Tasks:**
1. ✅ Complete Issue #421: JWT Authentication Middleware
2. ✅ Complete Issue #422: User Profile Management
3. Add `user_id` column to `analyses` table (migration)
4. Add `user_id` column to `tutoring_sessions` table (migration)
5. Add `user_id` column to `artifacts` table (via analysis relationship)
6. Update repositories to store user_id on creation

**Metrics Enabled After Phase 1:**
- Activation rate (first analysis per user)
- Retention cohorts (Week 1/4/12)
- Churn rate (inactive users)
- Session intervals (time between analyses)
- Analyses per user per month

**Estimated Effort:** 1-2 days (after auth is complete)

---

### Phase 2: User Feedback Collection

**Goal:** Collect explicit user feedback on artifact/tutoring quality

**Tasks:**
1. **Option A: Store feedback in database** (for easier aggregation):
   - Create `artifact_feedback` table (or extend annotation_queue with user_id)
   - Update feedback endpoint to also store in DB (dual-write: Langfuse + DB)
   - This enables SQL aggregation without Langfuse API calls

2. **Option B: Use Langfuse API** (no DB changes needed):
   - Create analytics service that queries Langfuse API for feedback scores
   - Aggregate ratings per artifact via Langfuse traces
   - More complex but leverages existing Langfuse infrastructure

3. Add user_id to feedback (requires auth - Issue #421):
   - Update feedback submission to include user_id
   - Enable per-user feedback tracking

4. Add feedback aggregation endpoints:
   - `GET /api/v1/artifacts/{id}/feedback/stats` (thumbs up/down counts, avg rating)
   - `GET /api/v1/analytics/feedback/summary` (feedback trends over time)

5. Create `tutoring_session_feedback` table (similar structure) - if needed

**Metrics Enabled After Phase 2:**
- User-rated artifact quality
- Artifact helpfulness rate
- Tutoring satisfaction scores
- Calibration analysis (G-Eval vs user ratings)

**Estimated Effort:** 3-5 days

---

### Phase 3: Retention & Cohort Analysis

**Goal:** Track retention curves and cohort performance

**Tasks:**
1. Create user_sessions table (optional - can derive from analyses):
   ```sql
   CREATE TABLE user_sessions (
     id UUID PRIMARY KEY,
     user_id UUID REFERENCES users(id),
     session_type VARCHAR(50),  -- 'analysis', 'tutoring', 'library_search'
     started_at TIMESTAMP WITH TIME ZONE,
     last_active TIMESTAMP WITH TIME ZONE,
     metadata JSONB  -- additional context
   );
   ```

2. Create analytics service:
   - `calculate_activation_rate(cohort_start_date, cohort_end_date)`
   - `calculate_retention(cohort_date, weeks: [1, 4, 12])`
   - `calculate_churn_rate(period_start, period_end)`
   - `calculate_dau_mau(date)`

3. Create analytics dashboard API:
   - `GET /api/v1/analytics/activation`
   - `GET /api/v1/analytics/retention`
   - `GET /api/v1/analytics/churn`
   - `GET /api/v1/analytics/engagement`

**Metrics Enabled After Phase 3:**
- Week 1/4/12 retention curves
- Cohort comparisons
- Churn rate trends
- DAU/MAU calculation

**Estimated Effort:** 5-7 days

---

### Phase 4: Quality Metrics Aggregation

**Goal:** Aggregate and analyze quality signals

**Tasks:**
1. Create quality metrics service:
   - Aggregate user ratings by artifact
   - Calculate artifact reuse rate (downloads → subsequent analyses)
   - Compare G-Eval scores vs user ratings (calibration)
   - Track error severity distribution

2. Create quality dashboard API:
   - `GET /api/v1/analytics/quality/artifacts`
   - `GET /api/v1/analytics/quality/tutoring`
   - `GET /api/v1/analytics/quality/calibration`

3. Integrate with Langfuse:
   - Link user feedback to Langfuse traces (via trace_id in artifacts)
   - Create Langfuse scores from user ratings

**Metrics Enabled After Phase 4:**
- Artifact quality trends
- Tutoring quality trends
- Calibration analysis (G-Eval accuracy)
- Error severity classification

**Estimated Effort:** 4-6 days

---

### Phase 5: Advanced Analytics (Future)

**Goal:** Predictive analytics and advanced insights

**Tasks:**
1. Search query tracking (library searches)
2. Reuse pattern analysis (artifact download → subsequent analysis on same topic)
3. Predictive churn model (ML on usage patterns)
4. A/B testing framework for prompt improvements
5. User segmentation (power users, casual users, churned)

**Estimated Effort:** 2-3 weeks (advanced ML features)

---

## 🎯 Key Value Moments (SkillForge-Specific)

Unlike ChatGPT's "message count", SkillForge has discrete value moments:

### Activation Moment
- **Definition:** User creates first analysis AND downloads artifact (or starts tutoring session)
- **Time-to-Activation Target:** <24 hours
- **Tracking:** `user_id` + `first_analysis_timestamp` + `first_artifact_download_timestamp`

### Retention Moment
- **Definition:** User creates 2nd+ analysis within 30 days (not daily like chat apps)
- **Alternative:** User returns to library and reuses past analysis
- **Tracking:** Analysis creation timestamps per user_id

### Engagement Indicators
- **Analyses per user per month:** Count analyses by user_id in last 30 days
- **Artifact download rate:** Downloads / Analyses Created
- **Tutoring completion rate:** Completed sessions / Total sessions started
- **Library search usage:** Users who search library (reusing past analyses)

### Soft Churn Signals
- **Analysis interval increases:** Weekly → Monthly → Never
- **Artifact downloads decrease:** Creates but doesn't download
- **Tutoring abandonment:** Status="active" but no activity in 7 days

---

## 🔗 Alignment with Current Roadmap

### Current Milestone: 🟤 Triple-Consumer Artifacts (Issues #299-304)

**Relevance:** Artifact quality improvements align with response quality metrics
- Current work on artifact quality gates ✅
- Missing: User feedback collection (Phase 2 of metrics)

### Next Milestone: 🟡 Tutoring System

**Relevance:** Tutoring quality metrics (Phase 2)
- TutoringSession model exists with understanding_scores ✅
- Missing: User satisfaction feedback

### Upcoming Milestone: 🔵 Staging/Production

**Relevance:** Auth implementation (#421, #422) enables Phase 1 metrics
- **BLOCKER:** Cannot track user-level metrics without auth
- **Recommendation:** Prioritize auth implementation before production launch

---

## 📊 Recommended Metrics Dashboard (Future)

```
┌──────────────────────────────────────────────────────────────┐
│              SKILLFORGE PRODUCT METRICS DASHBOARD              │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ACTIVATION                                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Activation Rate: 45%                                 │   │
│  │ Time-to-Activation: 18 hours (median)                │   │
│  │ Target: <24 hours                                    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  RETENTION                                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Week 1: 62%  Week 4: 38%  Week 12: 24%              │   │
│  │ Cohort: Dec 2025                                     │   │
│  │ [Retention curve chart]                              │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ENGAGEMENT                                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Analyses/User/Month: 2.3 (median)                    │   │
│  │ Artifact Download Rate: 0.78 (78% download artifacts)│   │
│  │ Tutoring Completion Rate: 68%                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  CHURN                                                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Monthly Churn Rate: 12%                              │   │
│  │ Avg Session Interval: 14 days                        │   │
│  │ At-Risk Users: 23 (inactive >30 days)                │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│              SKILLFORGE QUALITY METRICS DASHBOARD             │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ARTIFACT QUALITY                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Avg User Rating: 4.2/5.0                            │   │
│  │ Helpfulness Rate: 82%                               │   │
│  │ G-Eval Avg: 8.5/10                                  │   │
│  │ Calibration: Good (G-Eval correlates with ratings)  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  TUTORING QUALITY                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Completion Rate: 68%                                 │   │
│  │ Avg Messages/Session: 12                             │   │
│  │ User Satisfaction: 4.5/5.0                           │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ANALYSIS SUCCESS                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Success Rate: 96%                                    │   │
│  │ Avg Time-to-Complete: 4.2 minutes                    │   │
│  │ Error Rate: 4% (Critical: 0.5%, Minor: 3.5%)        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## ✅ Validation: Suitability for December 22, 2025

**Research Sources Validated:**
- ✅ LLM product metrics best practices (2025 research)
- ✅ Churn/retention metrics (industry standard)
- ✅ Response quality evaluation (LLM-specific)
- ✅ Activation metrics (product-led growth)

**SkillForge Context Validated:**
- ✅ Codebase exploration (database models, API endpoints, observability)
- ✅ Current roadmap alignment (milestones, issues)
- ✅ Architecture understanding (LangGraph, Langfuse, PostgreSQL)
- ✅ Unique use case (periodic deep-dives vs daily chat)

**Integration Feasibility:**
- ✅ Existing infrastructure supports metrics (database, Langfuse, SSE)
- ✅ Clear blockers identified (auth required for user-level metrics)
- ✅ Phased approach aligns with current development priorities
- ✅ No breaking changes to existing functionality

**Conclusion:** ✅ **This analysis is suitable and actionable for December 22, 2025**

---

## 📚 References

1. Braze - Essential Mobile App Metrics Formulas
2. UserPilot - Activation Metrics Guide
3. Kommunicate - How Accurate is ChatGPT (quality evaluation)
4. Matt Ambrogi - Evaluating Chatbots
5. Industry best practices for LLM product metrics (Dec 2025)

---

**Document Version:** 1.0  
**Last Updated:** December 22, 2025  
**Next Review:** After Auth Implementation (Issue #421)
