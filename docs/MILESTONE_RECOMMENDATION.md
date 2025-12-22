# 🎯 Milestone Recommendation: Feedback Analytics & Product Metrics

**Date:** December 22, 2025  
**Feature:** Langfuse-First Feedback Analytics + Product Metrics (Churn/Retention/Activation)

---

## 📊 Analysis Summary

### Current Milestone Landscape

**🔵 Staging/Production (Milestone #7)**
- **Due:** 2026-02-26
- **Description:** "Staging environment and production deployment readiness. Includes CI/CD, monitoring, and deployment infrastructure."
- **Open Issues:** 20
- **Key Related Issues:**
  - #86: "Monitoring & Logging" (includes monitoring dashboard with key metrics)
  - #421, #422, #420, #423: Auth implementation (REQUIRED for user-level metrics)
- **Roadmap Section:** 6.4 "Monitoring & Logging" explicitly mentions:
  - "Create monitoring dashboard"
  - "Track: API uptime, P95 latency, error rate, analysis completion rate"
  - "Monitoring dashboard shows key metrics"

**🔄 Langfuse Migration (Milestone #17)**
- **Due:** 2026-01-07 (earlier)
- **Description:** "Migrate from LangSmith to Langfuse for self-hosted observability"
- **Open Issues:** 13
- **Focus:** Observability infrastructure (traces, scores, LLM calls)
- **Related Work:** Annotation queues, quality scoring

---

## 🎯 Recommended Approach: **Split Across Two Milestones**

### Phase 1: Langfuse-First Architecture (Infrastructure)
**Milestone:** 🔄 **Langfuse Migration (#17)**

**Rationale:**
- Builds on existing Langfuse infrastructure
- Extends annotation/feedback system already in Langfuse Migration
- Infrastructure work (dual-write pattern, projection tables)
- Can be done in parallel with other Langfuse work
- Earlier milestone (Jan 7 vs Feb 26) = earlier infrastructure ready

**Scope:**
- Create PostgreSQL projection tables (`artifact_feedback_cache`, `artifact_metrics`)
- Implement dual-write pattern (Langfuse-first, then PostgreSQL)
- Add `_project_feedback_to_db()` method to `AnnotationService`
- Sync script to backfill from Langfuse (optional)

**Issues to Create:**
- "feat: Langfuse-First Feedback Analytics - PostgreSQL Projections"
  - Create projection tables
  - Implement dual-write pattern
  - Update `AnnotationService.submit_feedback()`

---

### Phase 2: Product Metrics & Analytics (Business Intelligence)
**Milestone:** 🔵 **Staging/Production (#7)**

**Rationale:**
- **Requires Auth** (Issues #421, #422 in Staging/Production)
- Product metrics (churn, retention, activation) are production readiness concerns
- Monitoring dashboard explicitly mentioned in Roadmap 6.4.4
- Needed for production decision-making (PMF signals)
- Fits with other monitoring/logging work in Staging/Production

**Scope:**
- Add user_id to feedback (after auth implemented)
- Create analytics service (retention, churn, activation calculations)
- Create analytics API endpoints
- Build monitoring dashboard with product metrics
- Integrate with existing monitoring infrastructure (Issue #86)

**Issues to Create:**
- "feat: Product Metrics Analytics - Retention, Churn, Activation"
  - Analytics service for cohort/retention calculations
  - API endpoints for metrics
  - Dashboard integration

---

## 📋 Detailed Recommendation

### Option A: Split (RECOMMENDED) ✅

**Phase 1 → Langfuse Migration (#17):**
- Infrastructure: PostgreSQL projections for fast queries
- Dual-write pattern implementation
- Foundation for analytics (data collection)

**Phase 2 → Staging/Production (#7):**
- Business intelligence: Metrics calculations
- Analytics endpoints
- Dashboard integration
- Requires auth (which is in this milestone)

**Benefits:**
- ✅ Infrastructure ready earlier (Jan 7)
- ✅ Clear separation: infrastructure vs business logic
- ✅ Aligns with auth dependency (must be in Staging/Production)
- ✅ Fits existing monitoring work in Staging/Production

---

### Option B: All in Staging/Production

**Everything → Staging/Production (#7)**

**Rationale:**
- Product metrics are production concerns
- All requires auth
- Dashboard is explicitly in Staging/Production roadmap

**Drawbacks:**
- ⚠️ Infrastructure work could be done earlier (Langfuse Migration is Jan 7)
- ⚠️ Less clear separation of concerns

---

### Option C: All in Langfuse Migration

**Everything → Langfuse Migration (#17)**

**Rationale:**
- Builds on Langfuse infrastructure
- Earlier milestone

**Drawbacks:**
- ❌ Requires auth (not in Langfuse Migration)
- ❌ Product metrics are production concerns, not observability infrastructure
- ❌ Dashboard not in Langfuse Migration scope

---

## ✅ Final Recommendation: **Option A (Split)**

### Phase 1: Infrastructure → 🔄 Langfuse Migration (#17)

**Issue Title:** "feat: Langfuse-First Feedback Analytics - PostgreSQL Projections"

**Tasks:**
1. Create `artifact_feedback_cache` table (migration)
2. Create `artifact_metrics` table (migration)
3. Add SQLAlchemy models
4. Implement `_project_feedback_to_db()` in `AnnotationService`
5. Update `submit_feedback()` for dual-write (Langfuse-first)
6. Add sync script (optional, for backfilling)

**Dependencies:** None (feedback collection already exists)

**Estimated Effort:** 3-5 days

---

### Phase 2: Analytics → 🔵 Staging/Production (#7)

**Issue Title:** "feat: Product Metrics Analytics - Retention, Churn, Activation"

**Tasks:**
1. Add user_id to feedback (after Issue #421 completed)
2. Create `AnalyticsService` (retention, churn, activation calculations)
3. Create analytics API endpoints:
   - `GET /api/v1/analytics/activation`
   - `GET /api/v1/analytics/retention`
   - `GET /api/v1/analytics/churn`
   - `GET /api/v1/artifacts/{id}/feedback/stats`
4. Integrate with monitoring dashboard (Issue #86)
5. Add frontend dashboard components (optional)

**Dependencies:** 
- Issue #421 (JWT Authentication) - REQUIRED
- Issue #86 (Monitoring & Logging) - Integration point

**Estimated Effort:** 5-7 days (after auth is ready)

---

## 🔗 Alignment with Existing Work

### Langfuse Migration (#17) Alignment
- ✅ Extends existing feedback system (already in Langfuse)
- ✅ Builds on annotation queue work
- ✅ Infrastructure-focused (projections, dual-write)
- ✅ Can leverage existing LangfuseService

### Staging/Production (#7) Alignment
- ✅ Requires auth (Issues #421, #422 in this milestone)
- ✅ Product metrics = production readiness
- ✅ Dashboard explicitly in roadmap 6.4.4
- ✅ Fits with monitoring/logging (Issue #86)
- ✅ Needed for PMF decision-making before full production

---

## 📝 Implementation Sequence

```
Timeline:
├─ Now → Jan 7 (Langfuse Migration)
│   └─ Phase 1: Infrastructure (projections, dual-write)
│       ✅ No dependencies
│       ✅ Can start immediately
│
├─ After Auth (#421) → Feb 26 (Staging/Production)
│   └─ Phase 2: Analytics (metrics, dashboard)
│       ⚠️ Blocks on: Issue #421 (auth)
│       ✅ Integrates with: Issue #86 (monitoring)
```

---

**Conclusion:** Split the work across both milestones - infrastructure in Langfuse Migration (earlier, no dependencies), analytics in Staging/Production (requires auth, fits monitoring dashboard scope).
