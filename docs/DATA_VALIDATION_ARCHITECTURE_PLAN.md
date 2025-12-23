# Data Validation & Read/Write Architecture Plan

**Date**: December 22, 2025  
**Status**: Research & Planning  
**Goal**: Implement production-grade data validation with proper read/write handling

**📋 IMPORTANT: raw_content vs content_ref Usage (Issue #244)**

Both `raw_content` and `content_ref` are required for completed workflows, but serve different purposes:

- **`raw_content`**: Full content string - used for embedding, chunking, quality gate (operations needing full content inline)
- **`content_ref`**: Handle Pattern reference - used for agent execution, state passing (on-demand loading via ArtifactStore)

**Validation Strategy:**
- Both are required for completed workflows (serve complementary purposes)
- `content_ref` validates Handle Pattern structure (uri, summary, etc.)
- `raw_content` validates content exists in database (stored by ArtifactStore)

See `docs/RAW_CONTENT_VS_CONTENT_REF_GUIDE.md` for detailed usage patterns.

---

## 🔍 Current Issues

### Issue 1: Weak Validation Logic

```
┌─────────────────────────────────────────────────────────────────┐
│              CURRENT VALIDATOR PROBLEMS                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Current Code:                                                  │
│  ```python                                                      │
│  for field in required_fields:                                 │
│      value = workflow_result.get(field)                        │
│      if not value:  # ❌ BUG: Fails for 0, False, [], ""        │
│          missing_fields.append(field)                          │
│  ```                                                            │
│                                                                  │
│  Problems:                                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ • if not value → False for 0, False, [], ""             │   │
│  │ • No type checking                                        │   │
│  │ • No distinction between None and empty values          │   │
│  │ • No validation of field structure (dict keys, list len) │   │
│  │ • No distinction between required vs optional            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Issue 2: Inconsistent Persistence Logic

```
┌─────────────────────────────────────────────────────────────────┐
│              CURRENT PERSISTER PROBLEMS                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Current Code:                                                  │
│  ```python                                                      │
│  raw_content = workflow_result.get("raw_content")              │
│  if raw_content:                                                │
│      analysis.raw_content = raw_content                         │
│  else:                                                          │
│      logger.warning(...)  # ❌ Logs warning but continues        │
│  ```                                                            │
│                                                                  │
│  Problems:                                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ • Validator rejects missing fields (fail fast)            │   │
│  │ • Persister silently continues (graceful degradation)     │   │
│  │ • Inconsistent behavior                                   │   │
│  │ • Partial data can be persisted                          │   │
│  │ • No database constraints to enforce integrity           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Issue 3: No Read Validation

```
┌─────────────────────────────────────────────────────────────────┐
│              MISSING READ VALIDATION                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Current:                                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ • Read from database                                      │   │
│  │ • Assume data is valid                                    │   │
│  │ • No validation on read                                   │   │
│  │ • Could serve incomplete/corrupted data                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Problem:                                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ • Old records might have incomplete data                  │   │
│  │ • Manual DB changes could corrupt data                    │   │
│  │ • No way to detect data integrity issues                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Best Practices for Data Validation

### Principle 1: Schema-Based Validation (Pydantic)

```
┌─────────────────────────────────────────────────────────────────┐
│              SCHEMA-BASED VALIDATION                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ✅ GOOD: Use Pydantic models                                   │
│  ```python                                                      │
│  class WorkflowResult(BaseModel):                              │
│      raw_content: str  # Required, non-empty                    │
│      extraction_metadata: ExtractionMetadata  # Required        │
│      content_embedding: list[float]  # Required, length=1536    │
│      artifact_id: str | None = None  # Optional                 │
│                                                                  │
│      @field_validator('raw_content')                            │
│      @classmethod                                               │
│      def validate_raw_content(cls, v: str) -> str:             │
│          if not v or not v.strip():                            │
│              raise ValueError("raw_content cannot be empty")   │
│          return v                                               │
│                                                                  │
│      @field_validator('content_embedding')                     │
│      @classmethod                                               │
│      def validate_embedding(cls, v: list[float]) -> list[float]:│
│          if len(v) != 1536:                                    │
│              raise ValueError(f"embedding must be 1536 dims, got {len(v)}")│
│          return v                                               │
│  ```                                                            │
│                                                                  │
│  Benefits:                                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ • Type-safe validation                                    │   │
│  │ • Automatic type conversion                               │   │
│  │ • Clear error messages                                    │   │
│  │ • Reusable across write and read                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Principle 2: Status-Aware Validation

```
┌─────────────────────────────────────────────────────────────────┐
│              STATUS-AWARE VALIDATION                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Different requirements based on workflow status:               │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Status: "completed"                                      │   │
│  │ Required:                                                │   │
│  │   ✅ raw_content (non-empty)                            │   │
│  │   ✅ extraction_metadata (with title)                    │   │
│  │   ✅ content_embedding (1536 dims)                       │   │
│  │   ✅ artifact_id (must exist)                            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Status: "failed"                                         │   │
│  │ Required:                                                │   │
│  │   ❌ raw_content (optional - might have failed early)     │   │
│  │   ❌ extraction_metadata (optional)                       │   │
│  │   ❌ content_embedding (optional)                         │   │
│  │   ✅ error_code (required for failures)                  │   │
│  │   ✅ error_message (required for failures)                │   │
│  │   ✅ failed_at_stage (required for failures)              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Status: "analyzing" (in-progress)                        │   │
│  │ Required:                                                │   │
│  │   ✅ raw_content (partial data is OK)                    │   │
│  │   ❌ extraction_metadata (optional until complete)        │   │
│  │   ❌ content_embedding (optional until complete)          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Principle 3: Validate on Both Read and Write

```
┌─────────────────────────────────────────────────────────────────┐
│              READ/WRITE VALIDATION STRATEGY                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Write Validation (Orchestrator → Database):                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 1. Validate workflow result structure                     │   │
│  │ 2. Validate field types and constraints                   │   │
│  │ 3. Validate business rules                                │   │
│  │ 4. Persist to database                                    │   │
│  │ 5. Database constraints enforce at DB level               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Read Validation (Database → API):                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 1. Read from database                                     │   │
│  │ 2. Validate against schema (for current status)           │   │
│  │ 3. Log warnings for invalid data (don't fail)            │   │
│  │ 4. Return validated data                                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Rationale:                                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ • Write: Fail fast (prevent bad data)                    │   │
│  │ • Read: Warn but serve (handle legacy/corrupted data)    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Proposed Architecture

### Component 1: Pydantic Schema for Workflow Results

```
┌─────────────────────────────────────────────────────────────────┐
│              WORKFLOW RESULT SCHEMA (Handle Pattern)            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ⚠️ IMPORTANT: Both raw_content and content_ref are required    │
│     They serve different purposes (see usage guide)              │
│                                                                  │
│  ```python                                                      │
│  from pydantic import BaseModel, Field, field_validator        │
│  from typing import Literal                                    │
│                                                                  │
│  class ExtractionMetadata(BaseModel):                          │
│      title: str                                                │
│      word_count: int = Field(ge=0)                             │
│      char_count: int = Field(ge=0)                             │
│      language: str | None = None                               │
│      # ... other metadata fields                               │
│                                                                  │
│  class ContentRef(BaseModel):                                  │
│      """Content reference for Handle Pattern (Issue #244)."""  │
│      uri: str = Field(..., pattern=r"^analysis://[a-f0-9-]+/content$")│
│      summary: str = Field(..., max_length=2000)                │
│      size_bytes: int = Field(..., ge=0)                        │
│      content_type: str                                         │
│      available_sections: list[str]                             │
│                                                                  │
│      @field_validator('uri')                                   │
│      @classmethod                                              │
│      def validate_uri(cls, v: str) -> str:                    │
│          """Validate URI format."""                            │
│          if not v.startswith("analysis://"):                  │
│              raise ValueError("URI must start with 'analysis://'")│
│          parts = v.split("/")                                  │
│          if len(parts) < 4 or parts[0] != "analysis:" or parts[1] != "":│
│              raise ValueError(f"Invalid URI format: {v}")      │
│          return v                                              │
│                                                                  │
│  class WorkflowResult(BaseModel):                              │
│      """Validated workflow result schema."""                   │
│                                                                  │
│      # Required fields for completed workflows (Handle Pattern)│
│      content_ref: ContentRef  # ⭐ NEW: Handle Pattern ref     │
│      raw_content: str = Field(..., min_length=1)  # For embedding, chunking│
│      extraction_metadata: ExtractionMetadata                    │
│      content_embedding: list[float] = Field(..., min_length=1536, max_length=1536)│
│                                                                  │
│      # Optional fields                                         │
│      artifact_id: str | None = None                            │
│      workflow_status: Literal["completed", "failed"] | None = None│
│      final_error: str | None = None                            │
│                                                                  │
│      @field_validator('content_ref')                           │
│      @classmethod                                              │
│      def validate_content_ref(cls, v: ContentRef | dict | None) -> ContentRef:│
│          """Validate content_ref exists and is properly formed."""│
│          if v is None:                                         │
│              raise ValueError("content_ref is required for completed workflows")│
│          if isinstance(v, dict):                               │
│              v = ContentRef.model_validate(v)                  │
│          return v                                              │
│                                                                  │
│      @field_validator('content_embedding')                    │
│      @classmethod                                              │
│      def validate_embedding(cls, v: list[float] | None) -> list[float] | None:│
│          """Ensure embedding has correct dimensions."""       │
│          if v is None:                                         │
│              return None                                       │
│          if len(v) != 1536:                                   │
│              raise ValueError(                                 │
│                  f"content_embedding must be 1536 dimensions, "│
│                  f"got {len(v)}"                              │
│              )                                                │
│          return v                                              │
│                                                                  │
│      def validate_for_status(self, status: str) -> list[str]: │
│          """Validate required fields for given status."""      │
│          missing: list[str] = []                              │
│                                                                  │
│          if status == "completed":                            │
│              # Handle Pattern fields required                  │
│              if not self.content_ref:                         │
│                  missing.append("content_ref")                │
│              if not self.extraction_metadata:                 │
│                  missing.append("extraction_metadata")        │
│              if not self.content_embedding:                   │
│                  missing.append("content_embedding")          │
│              if not self.artifact_id:                         │
│                  missing.append("artifact_id")                │
│              if not self.raw_content:                         │
│                  missing.append("raw_content")  # For embedding/chunking│
│                                                                  │
│          elif status == "failed":                             │
│              # No content fields required                     │
│              # Error fields validated separately              │
│              pass                                              │
│                                                                  │
│          return missing                                        │
│                                                                  │
│      def validate_content_exists(self, session: AsyncSession) -> bool:│
│          """Validate that content_ref URI points to existing content."""│
│          if not self.content_ref:                             │
│              return False                                      │
│          # Extract analysis_id from URI                        │
│          analysis_id = self.content_ref.uri.split("/")[2]     │
│          # Verify content exists in database                   │
│          # (ArtifactStore stores in Analysis.raw_content)     │
│          # ... implementation checks DB ...                    │
│          return True                                           │
│  ```                                                            │
│                                                                  │
│  Key Points:                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ • content_ref is REQUIRED (for Handle Pattern - agents)  │   │
│  │ • raw_content is REQUIRED (for embedding, chunking)      │   │
│  │ • Both serve different purposes - both needed            │   │
│  │ • content_ref.uri must be valid format                   │   │
│  │ • raw_content must exist in DB (stored by ArtifactStore) │   │
│  │ • Content existence should be validated                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Component 2: Enhanced Validator

```
┌─────────────────────────────────────────────────────────────────┐
│              ENHANCED VALIDATOR SERVICE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ```python                                                      │
│  from pydantic import ValidationError                          │
│                                                                  │
│  class WorkflowResultValidator:                                │
│      """Production-grade workflow result validator."""         │
│                                                                  │
│      def validate(                                             │
│          self,                                                 │
│          workflow_result: dict,                                │
│          expected_status: str = "completed",                   │
│      ) -> tuple[WorkflowResult | None, list[str]]:            │
│          """Validate workflow result and return validated object.│
│                                                                  │
│          Args:                                                 │
│              workflow_result: Raw workflow result dict          │
│              expected_status: Expected workflow status          │
│                                                                  │
│          Returns:                                              │
│              Tuple of (validated_result, validation_errors)   │
│              - validated_result: Pydantic model if valid, None if invalid│
│              - validation_errors: List of error messages       │
│          """                                                   │
│          try:                                                  │
│              # Parse and validate with Pydantic               │
│              validated = WorkflowResult.model_validate(        │
│                  workflow_result                                │
│              )                                                 │
│                                                                  │
│              # Status-specific validation                      │
│              missing = validated.validate_for_status(          │
│                  expected_status                                │
│              )                                                 │
│                                                                  │
│              if missing:                                       │
│                  return (                                      │
│                      None,                                     │
│                      [f"Missing required fields for {expected_status}: {missing}"],│
│                  )                                             │
│                                                                  │
│              return (validated, [])                            │
│                                                                  │
│          except ValidationError as e:                          │
│              # Extract Pydantic validation errors             │
│              errors = [                                        │
│                  f"{err['loc']}: {err['msg']}"                │
│                  for err in e.errors()                        │
│              ]                                                 │
│              return (None, errors)                             │
│                                                                  │
│          except Exception as e:                                │
│              # Catch-all for unexpected errors                 │
│              return (None, [f"Validation error: {str(e)}"])    │
│  ```                                                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Component 3: Status-Aware Orchestrator

```
┌─────────────────────────────────────────────────────────────────┐
│              STATUS-AWARE ORCHESTRATOR                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ```python                                                      │
│  result = await analysis_workflow.ainvoke(...)                 │
│                                                                  │
│  workflow_status = result.get("workflow_status")               │
│                                                                  │
│  if workflow_status == "failed":                               │
│      # Failed workflow - no validation needed                  │
│      logger.debug("workflow_failed", analysis_id=analysis_id)  │
│      # Status and error already set by workflow_failed node    │
│      return                                                    │
│                                                                  │
│  elif workflow_status == "completed":                          │
│      # Completed workflow - validate all fields                │
│      validator = WorkflowResultValidator()                     │
│      validated_result, errors = validator.validate(            │
│          result,                                               │
│          expected_status="completed"                           │
│      )                                                         │
│                                                                  │
│      if errors:                                                │
│          # Validation failed - this is unexpected              │
│          logger.error(                                         │
│              "workflow_result_validation_failed",              │
│              analysis_id=analysis_id,                          │
│              errors=errors,                                    │
│              message="Completed workflow has invalid data"     │
│          )                                                     │
│          await self.status_updater.update(                     │
│              analysis_id,                                      │
│              AnalysisStatus.ANALYSIS_FAILED.value              │
│          )                                                     │
│          await self.event_emitter.emit_error(                  │
│              analysis_id,                                      │
│              ValueError(f"Data validation failed: {errors}")  │
│          )                                                     │
│          return                                                │
│                                                                  │
│      # Validation passed - persist validated data              │
│      persist_success = await self.data_persister.persist(     │
│          analysis_id,                                          │
│          validated_result.model_dump()  # Use validated dict   │
│      )                                                         │
│                                                                  │
│  else:                                                          │
│      # Invalid workflow status                                 │
│      logger.error(                                             │
│          "invalid_workflow_status",                            │
│          analysis_id=analysis_id,                              │
│          status=workflow_status,                               │
│          message="Workflow returned invalid status"            │
│      )                                                         │
│      # ... handle error                                       │
│  ```                                                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Component 4: Enhanced Persister (Write Validation)

```
┌─────────────────────────────────────────────────────────────────┐
│              ENHANCED DATA PERSISTER                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ```python                                                      │
│  async def persist(                                            │
│      self,                                                     │
│      analysis_id: uuid.UUID,                                   │
│      workflow_result: dict | WorkflowResult,                   │
│      validate: bool = True,                                    │
│  ) -> bool:                                                    │
│      """Persist workflow results with validation."""          │
│                                                                  │
│      # Convert to Pydantic if dict provided                    │
│      if isinstance(workflow_result, dict):                     │
│          if validate:                                          │
│              try:                                              │
│                  validated = WorkflowResult.model_validate(    │
│                      workflow_result                            │
│                  )                                             │
│              except ValidationError as e:                      │
│                  logger.error(                                 │
│                      "persist_validation_failed",              │
│                      analysis_id=str(analysis_id),             │
│                      errors=e.errors(),                        │
│                  )                                             │
│                  raise ValueError(f"Invalid data: {e}") from e │
│          else:                                                 │
│              # Skip validation (for failed workflows)          │
│              validated = workflow_result                       │
│      else:                                                     │
│          # Already validated                                   │
│          validated = workflow_result                           │
│                                                                  │
│      async with AsyncSessionLocal() as db_session:            │
│          result = await db_session.execute(                    │
│              select(Analysis).where(Analysis.id == analysis_id).with_for_update()│
│          )                                                     │
│          analysis = result.scalar_one_or_none()                │
│                                                                  │
│          if not analysis:                                      │
│              raise ValueError(f"Analysis {analysis_id} not found")│
│                                                                  │
│          # Persist with type safety                            │
│          analysis.raw_content = validated.raw_content         │
│          analysis.extraction_metadata = validated.extraction_metadata.model_dump()│
│          analysis.content_embedding = validated.content_embedding│
│                                                                  │
│          # Title from metadata                                 │
│          if validated.extraction_metadata.title:              │
│              analysis.title = validated.extraction_metadata.title│
│                                                                  │
│          await db_session.commit()                             │
│          return True                                           │
│  ```                                                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Component 5: Read Validation (Repository Level)

```
┌─────────────────────────────────────────────────────────────────┐
│              READ VALIDATION (Repository)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ```python                                                      │
│  async def get_by_id(                                         │
│      self,                                                     │
│      analysis_id: uuid.UUID,                                   │
│      validate: bool = True,                                    │
│  ) -> Analysis | None:                                         │
│      """Get analysis with optional validation."""             │
│                                                                  │
│      result = await self.session.execute(                      │
│          select(Analysis).where(Analysis.id == analysis_id)    │
│      )                                                         │
│      analysis = result.scalar_one_or_none()                    │
│                                                                  │
│      if not analysis:                                          │
│          return None                                           │
│                                                                  │
│      if validate:                                              │
│          # Validate data integrity                             │
│          errors = self._validate_analysis_data(analysis)       │
│          if errors:                                            │
│              logger.warning(                                   │
│                  "read_validation_warning",                    │
│                  analysis_id=str(analysis_id),                 │
│                  status=analysis.status,                       │
│                  errors=errors,                                │
│                  message="Analysis data integrity issues detected"│
│              )                                                 │
│              # Don't fail - return data with warning           │
│                                                                  │
│      return analysis                                           │
│                                                                  │
│  def _validate_analysis_data(self, analysis: Analysis) -> list[str]:│
│      """Validate analysis data against expected schema."""    │
│      errors: list[str] = []                                   │
│                                                                  │
│      # Status-specific validation                              │
│      if analysis.status == "complete":                         │
│          if not analysis.raw_content:                          │
│              errors.append("complete analysis missing raw_content")│
│          if not analysis.content_embedding:                    │
│              errors.append("complete analysis missing embedding")│
│          if not analysis.extraction_metadata:                  │
│              errors.append("complete analysis missing metadata")│
│                                                                  │
│      # Type validation                                         │
│      if analysis.content_embedding:                            │
│          if len(analysis.content_embedding) != 1536:          │
│              errors.append(                                    │
│                  f"embedding has {len(analysis.content_embedding)} dims, expected 1536"│
│              )                                                 │
│                                                                  │
│      return errors                                             │
│  ```                                                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Validation Flow Visualization

### Complete Write Flow

```
┌─────────────────────────────────────────────────────────────────┐
│              WRITE VALIDATION FLOW                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Workflow Executes                                           │
│     result = await workflow.ainvoke(...)                        │
│     │                                                            │
│     ├─ workflow_status = result.get("workflow_status")         │
│     │                                                            │
│     └─ result (dict)                                            │
│                                                                  │
│  2. Check Workflow Status                                       │
│     │                                                            │
│     ├─ IF "failed":                                             │
│     │   └─ ✅ Skip validation (expected incomplete)             │
│     │                                                            │
│     └─ IF "completed":                                          │
│         │                                                        │
│         └─ 3. Validate Structure                                │
│             validator = WorkflowResultValidator()               │
│             validated, errors = validator.validate(             │
│                 result,                                         │
│                 expected_status="completed"                     │
│             )                                                   │
│             │                                                    │
│             ├─ IF errors:                                       │
│             │   ├─ ❌ Log error                                 │
│             │   ├─ ❌ Update status to "failed"                │
│             │   └─ ❌ Emit error event                          │
│             │                                                    │
│             └─ IF valid:                                        │
│                 │                                                │
│                 └─ 4. Persist Validated Data                    │
│                     await data_persister.persist(               │
│                         analysis_id,                            │
│                         validated.model_dump()  # Type-safe     │
│                     )                                           │
│                     │                                            │
│                     └─ ✅ Success                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Complete Read Flow

```
┌─────────────────────────────────────────────────────────────────┐
│              READ VALIDATION FLOW                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Repository Read                                             │
│     analysis = await repo.get_by_id(analysis_id, validate=True)│
│     │                                                            │
│     └─ SELECT * FROM analyses WHERE id = ?                     │
│                                                                  │
│  2. Validate Data Integrity                                     │
│     errors = _validate_analysis_data(analysis)                 │
│     │                                                            │
│     ├─ Check status-specific requirements                      │
│     ├─ Check field types and constraints                       │
│     └─ Check business rules                                    │
│                                                                  │
│  3. Handle Validation Results                                   │
│     │                                                            │
│     ├─ IF errors:                                              │
│     │   ├─ ⚠️ Log warning (don't fail)                         │
│     │   ├─ ⚠️ Return data anyway (handle gracefully)           │
│     │   └─ ⚠️ Frontend can show warnings                       │
│     │                                                            │
│     └─ IF valid:                                                │
│         └─ ✅ Return validated data                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Implementation Plan

### Phase 1: Pydantic Schemas

**Files to Create:**
- `backend/app/domains/analysis/schemas/workflow_result.py` (NEW)

**Tasks:**
1. Create `WorkflowResult` Pydantic model
2. Create `ExtractionMetadata` Pydantic model
3. Add field validators
4. Add status-aware validation method

**Acceptance Criteria:**
- ✅ Type-safe validation
- ✅ Proper handling of empty strings, None, etc.
- ✅ Status-aware field requirements

---

### Phase 2: Enhanced Validator

**Files to Create/Modify:**
- `backend/app/domains/analysis/services/workflow/validator.py` (REPLACE)

**Tasks:**
1. Replace simple validator with Pydantic-based validator
2. Add status-aware validation
3. Return structured validation errors

**Acceptance Criteria:**
- ✅ Uses Pydantic for validation
- ✅ Distinguishes None vs empty vs invalid
- ✅ Clear error messages

---

### Phase 3: Enhanced Persister

**Files to Modify:**
- `backend/app/domains/analysis/services/persistence/data_persister.py`

**Tasks:**
1. Accept `WorkflowResult` Pydantic model
2. Validate before persisting
3. Use validated data for persistence
4. Remove silent warnings

**Acceptance Criteria:**
- ✅ Validates before write
- ✅ Fails fast on invalid data
- ✅ No silent degradation

---

### Phase 4: Status-Aware Orchestrator

**Files to Modify:**
- `backend/app/domains/analysis/services/workflow/orchestrator.py`

**Tasks:**
1. Check workflow_status before validation
2. Use enhanced validator
3. Skip validation for failed workflows
4. Use validated data for persistence

**Acceptance Criteria:**
- ✅ No validation for failed workflows
- ✅ Proper validation for completed workflows
- ✅ Clear error messages

---

### Phase 5: Read Validation

**Files to Modify:**
- `backend/app/db/repositories/analysis_repository.py`

**Tasks:**
1. Add `validate` parameter to `get_by_id`
2. Implement `_validate_analysis_data`
3. Log warnings for invalid data
4. Return data even if validation fails

**Acceptance Criteria:**
- ✅ Validates on read
- ✅ Logs warnings (doesn't fail)
- ✅ Handles legacy/corrupted data gracefully

---

## 📐 Best Practices Compliance

### Data Integrity

```
┌─────────────────────────────────────────────────────────────────┐
│              DATA INTEGRITY CHECKLIST                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ✅ Schema Validation (Pydantic)                                │
│     ├─ Type checking                                            │
│     ├─ Constraint validation                                    │
│     └─ Custom validators                                        │
│                                                                  │
│  ✅ Status-Aware Validation                                     │
│     ├─ Different requirements per status                        │
│     ├─ Fail fast for required fields                           │
│     └─ Graceful degradation for optional fields                │
│                                                                  │
│  ✅ Write Validation                                            │
│     ├─ Validate before database write                          │
│     ├─ Database constraints as backup                          │
│     └─ Clear error messages                                    │
│                                                                  │
│  ✅ Read Validation                                             │
│     ├─ Validate on read (warning only)                         │
│     ├─ Handle legacy data gracefully                           │
│     └─ Log integrity issues                                    │
│                                                                  │
│  ✅ Consistent Behavior                                         │
│     ├─ Same validation logic for write and read                │
│     ├─ Reusable Pydantic models                                │
│     └─ No silent failures                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

**Status**: Ready for Implementation  
**Estimated Time**: 6-8 hours  
**Dependencies**: None (can be implemented incrementally)
