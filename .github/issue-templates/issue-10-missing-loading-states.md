## Problem

**Impact**: Single "LoadingState" for complex multi-stage analysis flow (extracting → analyzing → generating), poor UX as users don't understand what's happening during transitions and connection states.

### Root Causes

1. **Coarse-grained state** - Only "LoadingState" vs "CompletedState" vs "ErrorState"
2. **Missing SSE states** - No "Connecting", "Reconnecting", "Waiting for artifact"
3. **Unclear transitions** - User sees spinner without context
4. **No timeout feedback** - User doesn't know if system is stuck or working

### Technical Details

**Current state model (3 states):**
```typescript
type AnalysisState = 'loading' | 'completed' | 'error';

// Missing critical states:
// - Connecting to SSE stream
// - Reconnecting after disconnect
// - Waiting for first event
// - Waiting for artifact generation
// - Timeout approaching
// - Connection lost but retrying
```

**Real analysis flow (should have 8+ states):**
```
1. Initial load → Fetching analysis metadata
2. SSE connecting → Establishing real-time connection
3. SSE connected, waiting → Waiting for backend to start
4. Extracting → Content extraction in progress
5. Analyzing → Multi-agent analysis running
6. Generating → Artifact generation
7. Complete → Artifact ready
8. Reconnecting → Connection lost, retrying
9. Timeout warning → Taking longer than expected
```

## Impact Assessment

**Severity**: HIGH
**User Impact**: Confusion about what's happening, perceived as "stuck"
**Trust**: Users abandon thinking system is broken
**Support burden**: Users report "spinning forever" bugs

## Affected Files

```
frontend/src/features/analysis/
├── AnalyzeResult.tsx (single state check, no granularity)
├── components/
│   ├── LoadingState.tsx (generic spinner, no context)
│   └── AnalysisProgressCard.tsx (doesn't show connection state)
├── hooks/
│   └── useSSEStream.ts (doesn't expose connection states)
└── stores/
    └── analysisStore.ts (coarse state model)
```

## Acceptance Criteria

- [ ] Define granular state machine with 8+ states
- [ ] Show connection status ("Connecting...", "Reconnecting...")
- [ ] Show waiting states ("Waiting for analysis to start...")
- [ ] Show timeout warnings ("Taking longer than expected, please wait...")
- [ ] Show progress context ("Analyzing content - 2 of 8 stages complete")
- [ ] Smooth transitions between states (no jarring changes)
- [ ] User can see what system is doing at every moment
- [ ] All states have clear user-facing messages

## Verification Checklist

- [ ] No generic "Loading..." spinners without context
- [ ] Connection states visible (connecting, connected, reconnecting)
- [ ] Timeout states trigger after 30s with helpful message
- [ ] Can simulate each state in Storybook
- [ ] User testing confirms clarity of states
- [ ] No reported "stuck" bugs for normal operation
- [ ] All transitions logged for debugging
- [ ] Add E2E tests for all state transitions

## Suggested Implementation

### Phase 1: Define state machine (2-3 hours)
```typescript
// frontend/src/features/analysis/types/analysisStates.ts

export type AnalysisConnectionState =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'failed';

export type AnalysisProgressState =
  | 'idle'
  | 'waiting-for-start'
  | 'extracting'
  | 'analyzing'
  | 'generating'
  | 'completed'
  | 'failed';

export type AnalysisTimeoutState =
  | 'normal'
  | 'slow-warning'    // >30s
  | 'timeout-warning' // >60s
  | 'timeout-error';  // >120s

export interface AnalysisUIState {
  connection: AnalysisConnectionState;
  progress: AnalysisProgressState;
  timeout: AnalysisTimeoutState;

  // Computed helpers
  isLoading: boolean;
  canRetry: boolean;
  shouldShowWarning: boolean;
}
```

### Phase 2: Update useSSEStream hook (3-4 hours)
```typescript
// frontend/src/features/analysis/hooks/useSSEStream.ts

export const useSSEStream = (analysisId: string) => {
  const [connectionState, setConnectionState] = useState<AnalysisConnectionState>('disconnected');
  const [timeoutState, setTimeoutState] = useState<AnalysisTimeoutState>('normal');

  useEffect(() => {
    setConnectionState('connecting');

    const eventSource = new EventSource(`/api/sse/${analysisId}`);

    eventSource.onopen = () => {
      setConnectionState('connected');
      setTimeoutState('normal');
    };

    eventSource.onerror = () => {
      setConnectionState('reconnecting');
      // SSE auto-reconnects
    };

    // Timeout warnings
    const warningTimer = setTimeout(() => {
      setTimeoutState('slow-warning');
    }, 30_000); // 30s

    const timeoutTimer = setTimeout(() => {
      setTimeoutState('timeout-warning');
    }, 60_000); // 60s

    return () => {
      clearTimeout(warningTimer);
      clearTimeout(timeoutTimer);
      eventSource.close();
    };
  }, [analysisId]);

  return { connectionState, timeoutState };
};
```

### Phase 3: Create status message component (2 hours)
```typescript
// frontend/src/features/analysis/components/AnalysisStatusMessage.tsx

export const AnalysisStatusMessage = ({ uiState }: { uiState: AnalysisUIState }) => {
  const getMessage = () => {
    // Connection states
    if (uiState.connection === 'connecting') {
      return {
        icon: <Loader2 className="animate-spin" />,
        message: 'Connecting to analysis stream...',
        type: 'info' as const,
      };
    }

    if (uiState.connection === 'reconnecting') {
      return {
        icon: <RefreshCw className="animate-spin" />,
        message: 'Reconnecting...',
        type: 'warning' as const,
      };
    }

    // Timeout warnings
    if (uiState.timeout === 'slow-warning') {
      return {
        icon: <Clock />,
        message: 'Analysis is taking longer than expected, please wait...',
        type: 'warning' as const,
      };
    }

    if (uiState.timeout === 'timeout-warning') {
      return {
        icon: <AlertTriangle />,
        message: 'This is a complex analysis. It may take several minutes.',
        type: 'warning' as const,
      };
    }

    // Progress states
    if (uiState.progress === 'waiting-for-start') {
      return {
        icon: <Loader2 className="animate-spin" />,
        message: 'Waiting for analysis to start...',
        type: 'info' as const,
      };
    }

    if (uiState.progress === 'extracting') {
      return {
        icon: <FileText />,
        message: 'Extracting content from source...',
        type: 'info' as const,
      };
    }

    // ... other states
  };

  const { icon, message, type } = getMessage();

  return (
    <div className={`status-message status-${type}`}>
      {icon}
      <span>{message}</span>
    </div>
  );
};
```

### Phase 4: XState integration (optional, advanced)
```typescript
// For production-grade state management, consider XState
import { createMachine, interpret } from 'xstate';

const analysisMachine = createMachine({
  id: 'analysis',
  initial: 'disconnected',
  states: {
    disconnected: {
      on: { CONNECT: 'connecting' }
    },
    connecting: {
      on: {
        CONNECTED: 'connected',
        FAILED: 'failed'
      },
      after: {
        30000: { actions: 'showSlowWarning' }
      }
    },
    connected: {
      on: {
        START_EXTRACTION: 'extracting',
        DISCONNECT: 'reconnecting'
      }
    },
    // ... more states
  }
});
```

## User-Facing Messages Examples

| State | Message | Icon |
|-------|---------|------|
| Connecting | "Connecting to analysis stream..." | Spinner |
| Reconnecting | "Connection lost, reconnecting..." | Refresh |
| Waiting | "Waiting for analysis to start..." | Clock |
| Extracting | "Extracting content from source..." | FileText |
| Analyzing | "Analyzing content - 2 of 8 stages complete" | Zap |
| Generating | "Generating implementation guide..." | Sparkles |
| Slow warning | "Analysis taking longer than expected..." | Clock |
| Timeout warning | "Complex analysis, may take several minutes" | AlertTriangle |

## Benefits

1. **Clear UX**: User always knows what's happening
2. **Reduced anxiety**: No mysterious spinning
3. **Better debugging**: Can see exact state in logs
4. **Professional feel**: Polished experience
5. **Fewer support tickets**: Users understand system is working

## Related Issues

- Connects to SSE reliability improvements (#TBD)
- Relates to error handling enhancement (#TBD)
- May use XState for state management (#TBD)

## References

- XState: https://xstate.js.org/docs/
- UI state machines: https://kentcdodds.com/blog/application-state-management-with-react
- Loading states UX: https://www.nngroup.com/articles/progress-indicators/
