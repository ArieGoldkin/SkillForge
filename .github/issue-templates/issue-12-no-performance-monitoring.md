## Problem

**Impact**: Zero performance monitoring infrastructure - no React DevTools Profiler, no Web Vitals tracking, no render count logging, no metrics for the 647-line useSSEStream hook. Cannot detect performance regressions or validate optimizations.

### Root Causes

1. **No instrumentation** - No React Profiler wrapper, no performance marks
2. **No metrics collection** - Cannot measure render counts, re-render frequency, or hook execution time
3. **No visibility** - 1,600+ re-renders happen invisibly
4. **No regression detection** - Performance can degrade without anyone noticing
5. **No optimization validation** - Cannot prove optimizations worked

### Technical Details

**Missing monitoring:**
```typescript
// No React Profiler
<Profiler id="analysis-flow" onRender={logRenderMetrics}>
  <AnalyzeResult />
</Profiler>

// No Web Vitals
reportWebVitals(console.log);

// No render counting
const renderCount = useRef(0);
useEffect(() => {
  renderCount.current += 1;
  if (renderCount.current > 50) {
    console.warn('Excessive re-renders detected');
  }
});

// No performance marks
performance.mark('analysis-start');
// ... work ...
performance.measure('analysis-duration', 'analysis-start');
```

**Current situation:**
- Cannot see 1,600 re-renders happening
- Cannot measure SSE event processing time
- Cannot track Core Web Vitals (LCP, FID, CLS)
- Cannot prove optimizations reduce re-renders
- Cannot detect performance regressions in CI

## Impact Assessment

**Severity**: HIGH
**Developer Impact**: Flying blind on performance
**User Impact**: Cannot detect poor UX before it reaches production
**Optimization**: Cannot measure effectiveness of fixes
**Regression Risk**: Performance can degrade silently

## Affected Files

```
frontend/src/
├── features/analysis/
│   ├── AnalyzeResult.tsx (no profiling)
│   ├── hooks/useSSEStream.ts (647 lines, no metrics)
│   └── components/ (30+ components, no render counting)
├── App.tsx (no Web Vitals integration)
└── utils/ (missing performance utilities)
```

## Acceptance Criteria

- [ ] React Profiler integrated for analysis flow
- [ ] Web Vitals tracked (LCP, FID, CLS, TTFB)
- [ ] Render count logging for key components
- [ ] Performance marks for critical operations
- [ ] SSE event processing metrics
- [ ] Performance regression tests in CI
- [ ] Dashboard or logs showing metrics
- [ ] Alerts for excessive re-renders (>100 per analysis)

## Verification Checklist

- [ ] Can see render count in development console
- [ ] Can measure time from SSE event to UI update
- [ ] Can track Web Vitals in production
- [ ] Can detect 1,600+ re-renders and get alerted
- [ ] Can compare before/after metrics for optimizations
- [ ] CI fails if performance regresses
- [ ] Metrics logged to monitoring service (optional)
- [ ] All key user flows instrumented

## Suggested Implementation

### Phase 1: React Profiler Integration (2-3 hours)
```typescript
// frontend/src/components/PerformanceProfiler.tsx

import { Profiler, ProfilerOnRenderCallback } from 'react';

const onRenderCallback: ProfilerOnRenderCallback = (
  id,
  phase,
  actualDuration,
  baseDuration,
  startTime,
  commitTime,
) => {
  // Log slow renders
  if (actualDuration > 16) { // Slower than 60fps
    console.warn(`Slow render detected in ${id}:`, {
      phase,
      actualDuration: `${actualDuration.toFixed(2)}ms`,
      baseDuration: `${baseDuration.toFixed(2)}ms`,
    });
  }

  // Send to analytics (optional)
  if (window.analytics) {
    window.analytics.track('component_render', {
      component: id,
      duration: actualDuration,
      phase,
    });
  }
};

export const PerformanceProfiler: React.FC<{
  id: string;
  children: React.ReactNode;
}> = ({ id, children }) => {
  return (
    <Profiler id={id} onRender={onRenderCallback}>
      {children}
    </Profiler>
  );
};

// Usage
<PerformanceProfiler id="analysis-flow">
  <AnalyzeResult />
</PerformanceProfiler>
```

### Phase 2: Web Vitals Integration (1-2 hours)
```typescript
// frontend/src/utils/reportWebVitals.ts

import { onCLS, onFID, onFCP, onLCP, onTTFB } from 'web-vitals';

export const reportWebVitals = () => {
  const logMetric = (metric: any) => {
    console.log(metric.name, metric.value);

    // Send to analytics
    if (window.analytics) {
      window.analytics.track('web_vital', {
        name: metric.name,
        value: metric.value,
        rating: metric.rating,
      });
    }
  };

  onCLS(logMetric);  // Cumulative Layout Shift
  onFID(logMetric);  // First Input Delay
  onFCP(logMetric);  // First Contentful Paint
  onLCP(logMetric);  // Largest Contentful Paint
  onTTFB(logMetric); // Time to First Byte
};

// In main.tsx
import { reportWebVitals } from './utils/reportWebVitals';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

reportWebVitals();
```

### Phase 3: Render Count Tracking (2-3 hours)
```typescript
// frontend/src/hooks/useRenderCount.ts

import { useEffect, useRef } from 'react';

export const useRenderCount = (componentName: string, warnThreshold = 50) => {
  const renderCount = useRef(0);
  const startTime = useRef(Date.now());

  useEffect(() => {
    renderCount.current += 1;

    const elapsed = Date.now() - startTime.current;
    const rendersPerSecond = (renderCount.current / elapsed) * 1000;

    // Log in development
    if (import.meta.env.DEV) {
      console.log(`[${componentName}] Render #${renderCount.current}`);
    }

    // Warn on excessive renders
    if (renderCount.current > warnThreshold) {
      console.warn(
        `[${componentName}] Excessive renders detected!`,
        {
          total: renderCount.current,
          perSecond: rendersPerSecond.toFixed(2),
          elapsed: `${elapsed}ms`,
        }
      );
    }
  });

  return renderCount.current;
};

// Usage
export const StepItem = (props) => {
  const renderCount = useRenderCount('StepItem', 10);

  return <div data-render-count={renderCount}>...</div>;
};
```

### Phase 4: Performance Marks for Critical Paths (2 hours)
```typescript
// frontend/src/utils/performanceMarks.ts

export const performanceMarks = {
  markStart: (label: string) => {
    performance.mark(`${label}-start`);
  },

  markEnd: (label: string) => {
    const endMark = `${label}-end`;
    performance.mark(endMark);

    try {
      performance.measure(label, `${label}-start`, endMark);

      const measure = performance.getEntriesByName(label)[0];
      console.log(`⏱️ ${label}: ${measure.duration.toFixed(2)}ms`);

      // Cleanup
      performance.clearMarks(`${label}-start`);
      performance.clearMarks(endMark);
      performance.clearMeasures(label);

      return measure.duration;
    } catch (e) {
      console.warn(`Failed to measure ${label}:`, e);
      return null;
    }
  },
};

// Usage in SSE handler
export const useSSEStream = (analysisId: string) => {
  const handleMessage = (event: MessageEvent) => {
    performanceMarks.markStart('sse-event-processing');

    // Process event
    const data = JSON.parse(event.data);
    updateStore(data);

    const duration = performanceMarks.markEnd('sse-event-processing');

    if (duration && duration > 100) {
      console.warn('Slow SSE event processing:', duration);
    }
  };
};
```

### Phase 5: SSE Performance Metrics (2-3 hours)
```typescript
// frontend/src/features/analysis/hooks/useSSEMetrics.ts

export const useSSEMetrics = () => {
  const metrics = useRef({
    eventsReceived: 0,
    totalProcessingTime: 0,
    slowEvents: 0,
    reconnections: 0,
  });

  const trackEvent = (processingTime: number) => {
    metrics.current.eventsReceived += 1;
    metrics.current.totalProcessingTime += processingTime;

    if (processingTime > 50) {
      metrics.current.slowEvents += 1;
      console.warn('Slow SSE event:', processingTime);
    }

    // Log summary every 10 events
    if (metrics.current.eventsReceived % 10 === 0) {
      const avgTime = metrics.current.totalProcessingTime / metrics.current.eventsReceived;
      console.log('SSE Performance Summary:', {
        events: metrics.current.eventsReceived,
        avgProcessingTime: `${avgTime.toFixed(2)}ms`,
        slowEvents: metrics.current.slowEvents,
        reconnections: metrics.current.reconnections,
      });
    }
  };

  return { trackEvent, metrics: metrics.current };
};
```

### Phase 6: Performance Regression Tests (3-4 hours)
```typescript
// frontend/src/features/analysis/__tests__/performance.test.tsx

import { render } from '@testing-library/react';
import { vi } from 'vitest';

describe('Analysis Performance', () => {
  it('renders analysis flow in <100ms', () => {
    const start = performance.now();

    render(<AnalyzeResult analysisId="test-123" />);

    const duration = performance.now() - start;
    expect(duration).toBeLessThan(100);
  });

  it('re-renders <10 times on 50 SSE events', () => {
    const { rerender } = render(<AnalyzeResult />);

    let renderCount = 0;
    const originalRender = React.createElement;
    vi.spyOn(React, 'createElement').mockImplementation((...args) => {
      renderCount++;
      return originalRender(...args);
    });

    // Simulate 50 SSE events
    for (let i = 0; i < 50; i++) {
      act(() => {
        eventBus.emit('sse-event', { stage: 'analysis', progress: i });
      });
    }

    expect(renderCount).toBeLessThan(10);
  });

  it('processes SSE event in <50ms', () => {
    const handler = createSSEHandler();

    const start = performance.now();
    handler({ data: JSON.stringify({ stage: 'analysis' }) });
    const duration = performance.now() - start;

    expect(duration).toBeLessThan(50);
  });
});
```

### Phase 7: Development Dashboard (Optional, 4-5 hours)
```typescript
// frontend/src/components/PerformanceDashboard.tsx

export const PerformanceDashboard = () => {
  const [metrics, setMetrics] = useState({
    renders: {},
    webVitals: {},
    sseMetrics: {},
  });

  return (
    <div className="performance-dashboard">
      <h2>Performance Metrics</h2>

      <section>
        <h3>Component Renders</h3>
        {Object.entries(metrics.renders).map(([component, count]) => (
          <div key={component}>
            {component}: {count} renders
          </div>
        ))}
      </section>

      <section>
        <h3>Web Vitals</h3>
        <div>LCP: {metrics.webVitals.lcp}ms</div>
        <div>FID: {metrics.webVitals.fid}ms</div>
        <div>CLS: {metrics.webVitals.cls}</div>
      </section>

      <section>
        <h3>SSE Performance</h3>
        <div>Events: {metrics.sseMetrics.events}</div>
        <div>Avg Processing: {metrics.sseMetrics.avgTime}ms</div>
        <div>Slow Events: {metrics.sseMetrics.slowEvents}</div>
      </section>
    </div>
  );
};
```

## Monitoring Stack Options

### Option 1: DIY (Free)
- React Profiler + console.log
- Web Vitals logged to console
- Performance marks in browser DevTools
- Good for development, not production

### Option 2: Lightweight (Free tier)
- Sentry Performance Monitoring (free tier: 10k transactions/month)
- Vercel Analytics (free for hobby projects)
- LogRocket (free tier: 1k sessions/month)

### Option 3: Production-Grade (Paid)
- Datadog RUM (Real User Monitoring)
- New Relic Browser
- Dynatrace

## Success Metrics

After implementation, you should be able to answer:
- How many times does AnalyzeResult re-render per analysis? (Target: <100)
- What's the average SSE event processing time? (Target: <50ms)
- What's the LCP for the analysis page? (Target: <2.5s)
- How many slow renders occur per session? (Target: <5)

## Benefits

1. **Visibility**: See performance issues as they happen
2. **Validation**: Prove optimizations work
3. **Regression detection**: Catch performance degradation in CI
4. **User impact**: Understand real-world performance
5. **Data-driven**: Make optimization decisions based on metrics

## Related Issues

- Connects to excessive re-renders fix (#TBD)
- Validates optimization effectiveness (#TBD)
- Enables future performance improvements (#TBD)

## References

- React Profiler API: https://react.dev/reference/react/Profiler
- web-vitals library: https://github.com/GoogleChrome/web-vitals
- Performance API: https://developer.mozilla.org/en-US/docs/Web/API/Performance
- Performance testing: https://kentcdodds.com/blog/fix-the-slow-render-before-you-fix-the-re-render
