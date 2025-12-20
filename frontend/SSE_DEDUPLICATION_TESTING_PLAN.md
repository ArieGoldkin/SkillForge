# SSE Event Deduplication - Comprehensive Manual Testing Plan

## Overview
This document outlines a comprehensive testing plan for the SSE event deduplication logic implemented in Issue #404, using best practices from the sse.js library documentation.

## Testing Environment Setup

### Prerequisites
- SkillForge frontend running on http://localhost:5173
- Backend API running on http://localhost:8500
- Browser Developer Tools access
- Network tab monitoring capability

### Test Data Preparation
Create test scenarios that simulate real analysis workflows with duplicate events.

## Test Scenarios

### Scenario 1: Progress Event Deduplication
**Objective:** Verify that duplicate progress events for the same stage/status are deduplicated.

**Setup:**
```javascript
// Start analysis via UI
// Monitor Network tab for SSE connection
```

**Test Steps:**
1. Navigate to analysis page for a running analysis
2. Open Browser DevTools → Network tab → Filter by "EventSource"
3. Monitor SSE events in Console using structured logging
4. Look for multiple progress events with same `stage` and `status`

**Expected Results:**
- Only the most recent progress event for each stage/status combination should be retained
- Earlier events should be deduplicated automatically
- UI should reflect the latest progress state

**Verification:**
```javascript
// In browser console, check the SSE store state
window.useSSEStore.getState().events.filter(e => e.type === 'progress')
  .forEach(e => console.log(`${e.stage}:${e.status} - ${e.timestamp}`))
```

### Scenario 2: Complete Event Deduplication  
**Objective:** Verify that complete events are deduplicated by analysis ID.

**Setup:**
- Use backend to simulate multiple completion events for same analysis
- Monitor SSE events in real-time

**Test Steps:**
1. Trigger analysis completion
2. Force multiple completion events (if possible via backend)
3. Monitor event deduplication in store

**Expected Results:**
- Only one complete event per analysis should be retained
- Most recent complete event should be kept
- Analysis should transition to completed state

### Scenario 3: Error Event Deduplication
**Objective:** Verify error events are deduplicated by analysis + stage.

**Setup:**
- Simulate error conditions that might produce multiple errors for same stage

**Test Steps:**
1. Create conditions that trigger multiple errors for same analysis stage
2. Monitor error event deduplication
3. Verify only most recent error per stage is retained

### Scenario 4: Memory Management Under Load
**Objective:** Verify deduplication prevents memory bloat with high event volume.

**Setup:**
- Generate high volume of SSE events (50+ events)
- Include duplicates to test deduplication efficiency

**Test Steps:**
1. Monitor memory usage in Performance tab
2. Check event array size remains bounded
3. Verify deduplication prevents exponential growth

**Expected Results:**
- Event array should not exceed MAX_EVENTS (500)
- Memory usage should remain stable
- Critical events (errors, complete) should be prioritized

### Scenario 5: Connection Recovery
**Objective:** Verify deduplication works correctly after reconnection.

**Setup:**
- Force SSE disconnection and reconnection
- Ensure Last-Event-ID is properly handled

**Test Steps:**
1. Disconnect network briefly to trigger reconnection
2. Monitor that deduplication still works after reconnect
3. Check that stale events are not re-processed

**Expected Results:**
- Deduplication should work seamlessly across reconnections
- No duplicate events from reconnection
- State remains consistent

## Testing Tools & Techniques

### Browser Developer Tools
```javascript
// Monitor SSE events in real-time
const originalLog = console.log;
console.log = function(...args) {
  // Filter for SSE-related logs
  if (args[0]?.includes?.('[SSE]') || args[0]?.includes?.('Event deduplicated')) {
    originalLog.apply(console, args);
  }
};
```

### SSE Store Inspection
```javascript
// Real-time store monitoring
const store = window.useSSEStore.getState();
setInterval(() => {
  console.log('Events:', store.events.length);
  console.log('Latest event:', store.latestEvent);
  console.log('Duplicates removed:', /* track this somehow */);
}, 1000);
```

### Network Analysis
- Use Network tab to monitor EventSource connections
- Check for proper Last-Event-ID handling
- Verify reconnection behavior

## Success Criteria

### Functional Requirements
- ✅ Duplicate progress events (same stage+status) are deduplicated
- ✅ Duplicate complete events (same analysis) are deduplicated  
- ✅ Duplicate error events (same analysis+stage) are deduplicated
- ✅ Most recent events are always preserved
- ✅ Memory usage remains bounded under load
- ✅ Deduplication works across reconnections

### Performance Requirements
- ✅ Event processing < 10ms per event
- ✅ Memory growth < 1MB for 100 events
- ✅ No UI blocking during deduplication
- ✅ Reconnection recovery < 5 seconds

### Quality Requirements
- ✅ No console errors during testing
- ✅ All events properly logged with structured logging
- ✅ UI state remains consistent
- ✅ Error recovery works correctly

## Test Execution Checklist

### Pre-Test Setup
- [ ] Frontend running on localhost:5173
- [ ] Backend API running on localhost:8500  
- [ ] Browser DevTools prepared
- [ ] Network monitoring enabled
- [ ] Console logging configured

### Test Execution
- [ ] Scenario 1: Progress deduplication
- [ ] Scenario 2: Complete deduplication
- [ ] Scenario 3: Error deduplication  
- [ ] Scenario 4: Memory management
- [ ] Scenario 5: Connection recovery

### Post-Test Validation
- [ ] All success criteria met
- [ ] No regressions in existing functionality
- [ ] Performance metrics within limits
- [ ] Documentation updated with findings

## Automated Testing Integration

For future regression testing, consider:

```javascript
// Integration test for deduplication
describe('SSE Deduplication Integration', () => {
  it('should deduplicate events in real browser environment', async () => {
    // Use Playwright or Cypress to automate browser testing
    // Simulate SSE events via backend
    // Verify deduplication in store state
  });
});
```

## Findings & Recommendations

**Document any issues found during testing:**
- Performance bottlenecks
- Edge cases not covered
- UI inconsistencies
- Memory leaks

**Recommendations for production monitoring:**
- Add metrics for deduplication efficiency
- Monitor event processing latency
- Alert on excessive memory usage
- Track deduplication ratios
