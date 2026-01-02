---
name: branded-types
description: Branded types for type-safe IDs (Zod + Python NewType)
version: 1.0.0
tags: [typescript, python, branded-types, type-safety]
size: atomic
domain: frontend
---

# Branded Types

Prevent mixing different ID types at compile time.

## TypeScript (Zod)

```typescript
import { z } from 'zod'

// Define branded types
const UserId = z.string().uuid().brand<'UserId'>()
const AnalysisId = z.string().uuid().brand<'AnalysisId'>()

type UserId = z.infer<typeof UserId>
type AnalysisId = z.infer<typeof AnalysisId>

// Functions require specific ID types
function deleteAnalysis(id: AnalysisId): void { ... }
function getUser(id: UserId): User { ... }

// Usage
const userId: UserId = UserId.parse('...')
const analysisId: AnalysisId = AnalysisId.parse('...')

deleteAnalysis(analysisId)  // ✅ OK
deleteAnalysis(userId)      // ❌ Error: UserId not assignable to AnalysisId
```

## Python (NewType)

```python
from typing import NewType
from uuid import UUID

# Define branded types (zero runtime overhead)
AnalysisID = NewType("AnalysisID", UUID)
ArtifactID = NewType("ArtifactID", UUID)

# Factory functions for validation
def create_analysis_id(value: UUID | str) -> AnalysisID:
    if isinstance(value, str):
        value = UUID(value)
    return AnalysisID(value)

def create_artifact_id(value: UUID | str) -> ArtifactID:
    if isinstance(value, str):
        value = UUID(value)
    return ArtifactID(value)

# Type checker prevents mixing
def delete_analysis(id: AnalysisID) -> None: ...

analysis_id = create_analysis_id("...")
artifact_id = create_artifact_id("...")

delete_analysis(analysis_id)   # ✅ OK
delete_analysis(artifact_id)   # ❌ Error (mypy/ty)
```

## Why Use Branded Types?

| Benefit | Description |
|---------|-------------|
| Compile-time safety | Catch ID mixing before runtime |
| Self-documenting | Function signatures show ID type |
| Zero runtime cost | Python NewType compiles away |
| Centralized validation | Factory functions validate format |

## Best Practices

- ✅ Use for all entity IDs (User, Analysis, Artifact)
- ✅ Create factory functions for validation
- ✅ TypeScript: Use Zod `.brand<>()`
- ✅ Python: Use `NewType` (not Pydantic for IDs)
