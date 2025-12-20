## Problem

**Impact**: Stage configurations duplicated across 3 files (661 total lines), update in one place causes bugs when other copies are forgotten, triple maintenance burden.

### Root Causes

1. **Triple definition** - Stage configs in stageConfig.ts (245 lines), constants.ts (137 lines), sseNormalizer.ts (279 lines)
2. **No single source of truth** - Each file has slightly different structure
3. **Update hell** - Changing stage requires editing 3 files or risk inconsistency
4. **Hidden bugs** - Missing updates in one file cause runtime errors

### Technical Details

**Duplication breakdown:**
```
1. stageConfig.ts (245 lines)
   - Stage metadata: order, title, description, category
   - Used by: Progress display components

2. constants.ts (137 lines)
   - Stage icons, status mappings
   - Used by: Status badges, visual indicators

3. sseNormalizer.ts (279 lines)
   - SSE event normalization, stage name mappings
   - Used by: Real-time event processing

Total: 661 lines of duplicated configuration
Overlap: ~70% of information is redundant
```

**Example of duplication:**
```typescript
// stageConfig.ts
{ id: 'extraction', title: 'Content Extraction', order: 1 }

// constants.ts
const STAGE_ICONS = { extraction: FileText }

// sseNormalizer.ts
case 'extraction_started': return 'extraction'
```

## Impact Assessment

**Severity**: HIGH
**Developer Impact**: Every stage change touches 3 files
**Bug Risk**: High - forgetting one file causes runtime errors
**Code Bloat**: 661 lines, ~400 could be eliminated

## Affected Files

```
frontend/src/features/analysis/
├── hooks/
│   └── stageConfig.ts (245 lines) - Main stage metadata
├── components/progress/
│   ├── constants.ts (137 lines) - Icons and status
│   └── sseNormalizer.ts (279 lines) - Event normalization
└── types/
    └── analysis.types.ts (needs centralized types)
```

## Acceptance Criteria

- [ ] Create single `stageRegistry.ts` as source of truth
- [ ] Consolidate all stage metadata into one definition per stage
- [ ] Eliminate 400+ lines of duplicate code
- [ ] All 3 original files import from registry
- [ ] Zero functional regressions
- [ ] Adding new stage touches only 1 file
- [ ] TypeScript ensures all required fields present

## Verification Checklist

- [ ] All stage metadata in single registry file
- [ ] stageConfig.ts imports from registry (no duplication)
- [ ] constants.ts imports from registry (no duplication)
- [ ] sseNormalizer.ts imports from registry (no duplication)
- [ ] Line count reduced by 400+ lines
- [ ] All existing tests pass
- [ ] Can add new stage by editing only registry
- [ ] TypeScript catches missing fields at compile time

## Suggested Implementation

### Phase 1: Create StageRegistry (2-3 hours)
```typescript
// frontend/src/features/analysis/config/stageRegistry.ts

import { FileText, Zap, Target, Shield, CheckCircle } from 'lucide-react';

export interface StageDefinition {
  id: string;
  order: number;
  title: string;
  description: string;
  category: 'extraction' | 'analysis' | 'generation';
  icon: React.ComponentType;

  // SSE normalization
  eventMappings: {
    started: string;
    completed: string;
    failed: string;
  };

  // Status display
  statusConfig: {
    pendingColor: string;
    activeColor: string;
    completeColor: string;
  };
}

export const STAGE_REGISTRY: Record<string, StageDefinition> = {
  extraction: {
    id: 'extraction',
    order: 1,
    title: 'Content Extraction',
    description: 'Extracting content from source',
    category: 'extraction',
    icon: FileText,
    eventMappings: {
      started: 'extraction_started',
      completed: 'extraction_completed',
      failed: 'extraction_failed',
    },
    statusConfig: {
      pendingColor: 'gray',
      activeColor: 'blue',
      completeColor: 'green',
    },
  },
  // ... other stages
};

// Helper functions
export const getStageById = (id: string) => STAGE_REGISTRY[id];
export const getAllStages = () => Object.values(STAGE_REGISTRY).sort((a, b) => a.order - b.order);
export const getStageIcon = (id: string) => STAGE_REGISTRY[id]?.icon;
```

### Phase 2: Refactor existing files (3-4 hours)
```typescript
// stageConfig.ts - NOW JUST IMPORTS
import { STAGE_REGISTRY, getAllStages } from '../config/stageRegistry';

export const getStageConfig = (id: string) => STAGE_REGISTRY[id];

// constants.ts - NOW JUST IMPORTS
import { getStageIcon } from '../config/stageRegistry';

export const STAGE_ICONS = Object.fromEntries(
  Object.entries(STAGE_REGISTRY).map(([id, stage]) => [id, stage.icon])
);

// sseNormalizer.ts - NOW USES REGISTRY
import { STAGE_REGISTRY } from '../config/stageRegistry';

const normalizeEventType = (event: string): string => {
  for (const stage of Object.values(STAGE_REGISTRY)) {
    if (event === stage.eventMappings.started) return stage.id;
    if (event === stage.eventMappings.completed) return stage.id;
    if (event === stage.eventMappings.failed) return stage.id;
  }
  return event;
};
```

### Phase 3: Add type safety (1 hour)
```typescript
// Ensure all stages have required fields at compile time
type StageId = keyof typeof STAGE_REGISTRY;

// Ensure event mappings are complete
type RequiredEventMappings = 'started' | 'completed' | 'failed';
```

## Benefits

1. **Single source of truth**: Update once, propagates everywhere
2. **Reduced code**: Eliminate 400+ duplicate lines
3. **Type safety**: TypeScript ensures completeness
4. **Easier maintenance**: New stage = one definition
5. **No hidden bugs**: Cannot forget to update one file

## Related Issues

- Relates to type safety improvements (#TBD)
- Connects to testing simplification (#TBD)

## References

- DRY Principle: https://en.wikipedia.org/wiki/Don%27t_repeat_yourself
- TypeScript const assertions: https://www.typescriptlang.org/docs/handbook/release-notes/typescript-3-4.html#const-assertions
