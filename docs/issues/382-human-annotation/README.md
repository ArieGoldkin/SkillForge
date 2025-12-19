# Issue #382: Add Human Annotation Workflow

**Status:** 📋 Planned
**Branch:** `issue/378-385-langfuse-phase2`
**Milestone:** Langfuse Migration Phase 2
**Priority:** 🔵 LOW (Nice-to-have)
**Estimated Effort:** 6-8 hours
**Dependencies:** Issue #378 (Session & User Tracking), Issue #372 (Langfuse Migration)

---

## Summary

Implement human annotation workflow to capture user feedback and reviewer judgments on analysis quality. This enables quality feedback loops through:
- Automatic queuing of low-quality outputs for review
- User thumbs up/down feedback on artifacts  
- Detailed reviewer annotations (1-10 scores)
- Integration with Langfuse annotation queues and score configs

**Note**: This is a LOW priority enhancement for quality improvement, not required for core functionality.

## Key Features

- **Auto-queuing**: Quality gate flags outputs with avg_score <  0.6 for review
- **User feedback**: Thumbs up/down buttons on artifact pages
- **Reviewer dashboard**: Annotation queue page for detailed scoring
- **Langfuse integration**: Submit scores with score configs
- **Feedback loop**: Annotations inform prompt improvements and A/B tests

## Architecture

See full documentation for detailed architecture diagram showing:
- Auto-queuing from quality_gate_node.py
- User feedback capture via FeedbackButtons component
- Annotation dashboard with scoring form
- Langfuse score submission with configs

## Implementation Checklist

### Phase 1: Backend (3 hours)
- [ ] Create annotation_service.py (queue, feedback, submit methods)
- [ ] Create API endpoints (POST /queue, POST /feedback, GET /queue)
- [ ] Add annotations database table (migration)
- [ ] Update quality_gate_node.py to auto-queue low scores

### Phase 2: Frontend (2 hours)  
- [ ] Create FeedbackButtons.tsx component
- [ ] Create AnnotationQueuePage.tsx dashboard
- [ ] Integrate feedback buttons in ArtifactPage.tsx

### Phase 3: Langfuse Config (1 hour)
- [ ] Create 4 score configs in Langfuse UI
- [ ] Create annotation queue
- [ ] Add env vars for config IDs

### Phase 4: Testing (2 hours)
- [ ] Unit tests for annotation service
- [ ] Integration tests for full workflow
- [ ] Manual testing with Langfuse UI

## Score Configurations

1. **user-feedback-binary**: Thumbs up/down (BOOLEAN)
2. **annotation-relevance**: 1-10 categorical
3. **annotation-depth**: 1-10 categorical
4. **annotation-coherence**: 1-10 categorical

## Files to Create

**Backend**:
- `backend/app/shared/services/annotations/annotation_service.py`
- `backend/app/api/v1/annotations.py`
- `backend/app/db/models/annotation.py`
- `backend/alembic/versions/XXX_add_annotations_table.py`

**Frontend**:
- `frontend/src/features/analysis/components/FeedbackButtons.tsx`
- `frontend/src/features/annotations/pages/AnnotationQueuePage.tsx`

## Related Issues

- **#378**: Session & User Tracking (required for trace attribution)
- **#379**: Prompt Management (annotations inform A/B testing)
- **#383**: Token/Cost Tracking (measure annotation impact)
- **#381**: LLM-as-Judge (complementary evaluation method)

---

**See agent task a724b5a output for complete 800+ line detailed documentation.**
