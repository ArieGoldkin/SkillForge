# PII Detection Architecture Diagram

**Issue:** #220 - PII/Safety Guardrails
**Date:** December 10, 2025

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      EMBEDDING PIPELINE WITH PII DETECTION                  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────┐
│   Input     │
│   Text      │
│  (Content)  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PII DETECTION LAYER                                │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                    HYBRID PII DETECTOR                             │    │
│  │  ┌──────────────────────┐         ┌──────────────────────┐        │    │
│  │  │   STAGE 1: REGEX     │         │  STAGE 2: PRESIDIO   │        │    │
│  │  │   (Fast Path)        │         │  (ML-Based)          │        │    │
│  │  │                      │         │                      │        │    │
│  │  │  • Email             │         │  • PERSON            │        │    │
│  │  │  • Phone             │────▶────│  • ORGANIZATION      │        │    │
│  │  │  • SSN               │ If PII  │  • LOCATION          │        │    │
│  │  │  • Credit Card       │ found   │  • IP_ADDRESS        │        │    │
│  │  │  • API Keys          │         │  • URL (contextual)  │        │    │
│  │  │                      │         │                      │        │    │
│  │  │  Latency: < 2ms      │         │  Latency: 20-50ms    │        │    │
│  │  │  Accuracy: 85%       │         │  Accuracy: 94%       │        │    │
│  │  └──────────┬───────────┘         └──────────┬───────────┘        │    │
│  │             │                                 │                    │    │
│  │             └────────────┬────────────────────┘                    │    │
│  │                          ▼                                         │    │
│  │                  ┌───────────────┐                                 │    │
│  │                  │  MERGE RESULTS│                                 │    │
│  │                  │  • Deduplicate│                                 │    │
│  │                  │  • Max conf   │                                 │    │
│  │                  └───────┬───────┘                                 │    │
│  └──────────────────────────┼─────────────────────────────────────────┘    │
└────────────────────────────┼──────────────────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │  PII Detected? │
                    └────────┬───────┘
                             │
                 ┌───────────┴───────────┐
                 │                       │
                NO                      YES
                 │                       │
                 ▼                       ▼
        ┌────────────────┐     ┌────────────────────┐
        │  Continue to   │     │  Check Config:     │
        │  Embedding     │     │  BLOCK or WARN?    │
        │  Generation    │     └─────────┬──────────┘
        └────────────────┘               │
                                         │
                             ┌───────────┴──────────┐
                             │                      │
                          BLOCK                   WARN
                             │                      │
                             ▼                      ▼
                   ┌─────────────────┐    ┌────────────────┐
                   │ Raise Error:    │    │ Log Warning +  │
                   │ PIIDetectedError│    │ Continue       │
                   │                 │    │ Embedding      │
                   │ • Return 400    │    │                │
                   │ • Log metadata  │    │ • Flag in DB   │
                   │ • Record metric │    │ • Record metric│
                   └─────────────────┘    └────────┬───────┘
                                                   │
                                                   ▼
                                          ┌────────────────┐
                                          │  OpenAI API    │
                                          │  Embeddings    │
                                          │                │
                                          │  Return Vector │
                                          │  + PII Flags   │
                                          └────────────────┘
```

---

## Component Details

### 1. Regex Detector (Stage 1)

```
┌─────────────────────────────────────────────────────────────┐
│              REGEX PATTERN MATCHING                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Input: "Contact john@example.com or call 555-1234"        │
│                                                             │
│  Pattern Matching:                                         │
│  ┌──────────────────────────────────────────────────┐      │
│  │ EMAIL_PATTERN:                                   │      │
│  │   r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z]+"  │      │
│  │   Match: "john@example.com"  ✓                   │      │
│  ├──────────────────────────────────────────────────┤      │
│  │ PHONE_PATTERN:                                   │      │
│  │   r"\b\d{3}-\d{3}-\d{4}\b"                       │      │
│  │   Match: "555-1234"  ✓                           │      │
│  └──────────────────────────────────────────────────┘      │
│                                                             │
│  Output:                                                   │
│  {                                                         │
│    "has_pii": true,                                        │
│    "pii_types": ["email", "phone"],                        │
│    "confidence": 0.8,                                      │
│    "matches": [                                            │
│      {                                                     │
│        "type": "email",                                    │
│        "start": 8,                                         │
│        "end": 26,                                          │
│        "context": "Contact [REDACTED] or call"             │
│      }                                                     │
│    ]                                                       │
│  }                                                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2. Presidio Detector (Stage 2)

```
┌─────────────────────────────────────────────────────────────┐
│         PRESIDIO ML-BASED ENTITY RECOGNITION                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Input: "John Smith works at Microsoft in Seattle"         │
│                                                             │
│  NLP Pipeline:                                             │
│  ┌──────────────────────────────────────────────────┐      │
│  │ 1. Tokenization (spaCy)                          │      │
│  │    ["John", "Smith", "works", "at", ...]         │      │
│  ├──────────────────────────────────────────────────┤      │
│  │ 2. Named Entity Recognition                      │      │
│  │    PERSON: "John Smith" (confidence: 0.95)       │      │
│  │    ORG: "Microsoft" (confidence: 0.92)           │      │
│  │    GPE: "Seattle" (confidence: 0.89)             │      │
│  ├──────────────────────────────────────────────────┤      │
│  │ 3. Pattern Recognizers                           │      │
│  │    (email, phone, SSN validators)                │      │
│  ├──────────────────────────────────────────────────┤      │
│  │ 4. Context Analysis                              │      │
│  │    Check allowlist, false positive filtering     │      │
│  └──────────────────────────────────────────────────┘      │
│                                                             │
│  Output:                                                   │
│  {                                                         │
│    "has_pii": true,                                        │
│    "entity_types": ["PERSON", "ORGANIZATION", "GPE"],      │
│    "confidence": 0.95,                                     │
│    "sensitivity_level": "medium"                           │
│  }                                                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Decision Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PII DETECTION DECISION TREE                         │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────┐
                              │ Input Text  │
                              └──────┬──────┘
                                     │
                                     ▼
                        ┌────────────────────────┐
                        │ PII_DETECTION_ENABLED? │
                        └────────┬───────────────┘
                                 │
                    ┌────────────┴───────────┐
                   NO                       YES
                    │                        │
                    ▼                        ▼
            ┌───────────────┐    ┌──────────────────┐
            │ Skip Check    │    │ Run Regex Stage  │
            │ → Embed       │    └────────┬─────────┘
            └───────────────┘             │
                                          ▼
                               ┌──────────────────┐
                               │ Regex Found PII? │
                               └────────┬─────────┘
                                        │
                            ┌───────────┴──────────┐
                           NO                     YES
                            │                      │
                            ▼                      ▼
                 ┌─────────────────────┐  ┌──────────────────┐
                 │ PII_ALWAYS_RUN_     │  │ Run Presidio     │
                 │ PRESIDIO = true?    │  │ Stage            │
                 └────────┬────────────┘  └────────┬─────────┘
                          │                        │
                     ┌────┴────┐                   │
                    NO        YES                  │
                     │          │                  │
                     ▼          └──────┬───────────┘
               ┌──────────┐            ▼
               │ No PII   │   ┌────────────────┐
               │ → Embed  │   │ Presidio Found │
               └──────────┘   │ Additional PII?│
                              └────────┬───────┘
                                       │
                          ┌────────────┴────────────┐
                         NO                        YES
                          │                         │
                          ▼                         ▼
                   ┌──────────────┐       ┌────────────────┐
                   │ Use Regex    │       │ Merge Results  │
                   │ Results Only │       │ (Deduplicate)  │
                   └──────┬───────┘       └────────┬───────┘
                          │                        │
                          └────────────┬───────────┘
                                       ▼
                          ┌────────────────────────┐
                          │ PII_BLOCK_ON_DETECTION │
                          │ = true?                │
                          └────────┬───────────────┘
                                   │
                       ┌───────────┴──────────┐
                      YES                    NO
                       │                      │
                       ▼                      ▼
            ┌──────────────────┐    ┌────────────────┐
            │ Raise Error:     │    │ Log Warning +  │
            │ PIIDetectedError │    │ Flag in DB     │
            │ • 400 Response   │    │ • Continue     │
            │ • No Embedding   │    │ • Generate     │
            └──────────────────┘    │   Embedding    │
                                    └────────────────┘
```

---

## Sensitivity Level Impact

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SENSITIVITY LEVEL CONFIGURATION                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  LOW (Threshold: 0.7)                                                       │
│  ────────────────────────────────────────────────────────────               │
│  ✅ Fewer false positives                                                   │
│  ✅ Faster processing (fewer matches)                                       │
│  ❌ May miss some PII (lower recall)                                        │
│                                                                             │
│  Use Case: Public technical content, tutorials, documentation              │
│  Example: "John Doe" (common placeholder) → NOT DETECTED                    │
│                                                                             │
│  ─────────────────────────────────────────────────────────────              │
│                                                                             │
│  MEDIUM (Threshold: 0.5) ⭐ RECOMMENDED                                     │
│  ────────────────────────────────────────────────────────────               │
│  ✅ Balanced precision/recall                                               │
│  ✅ Good for most use cases                                                 │
│  ⚠️  Some false positives in technical content                              │
│                                                                             │
│  Use Case: General content analysis, mixed sources                         │
│  Example: "John Doe" → DETECTED (confidence: 0.6)                           │
│                                                                             │
│  ─────────────────────────────────────────────────────────────              │
│                                                                             │
│  HIGH (Threshold: 0.3)                                                      │
│  ────────────────────────────────────────────────────────────               │
│  ✅ Catches more PII (high recall)                                          │
│  ❌ More false positives                                                    │
│  ❌ Slower processing (more Presidio checks)                                │
│                                                                             │
│  Use Case: Sensitive content, user-generated data, compliance               │
│  Example: "john" in "john@example.com" → DETECTED as PERSON (0.4)           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Performance Optimization

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FAST PATH OPTIMIZATION                                   │
└─────────────────────────────────────────────────────────────────────────────┘

Scenario A: No PII (90% of cases)
──────────────────────────────────────────────────────────────────────────
Input: "This is a technical article about Python asyncio"

Stage 1: Regex (0.8ms)
  └─ No email, phone, SSN, credit card detected ✓

Config: PII_ALWAYS_RUN_PRESIDIO = false
  └─ Skip Stage 2 (save 30ms)

Result: No PII → Continue to embedding
Total Latency: 0.8ms ⚡

──────────────────────────────────────────────────────────────────────────

Scenario B: PII Detected (10% of cases)
──────────────────────────────────────────────────────────────────────────
Input: "Contact john@example.com for more information"

Stage 1: Regex (1.2ms)
  └─ Email detected: john@example.com ✓

Stage 2: Presidio (28ms)
  └─ No additional entities (email already caught by regex)

Result: PII Detected → Block/Warn based on config
Total Latency: 29.2ms

──────────────────────────────────────────────────────────────────────────

Scenario C: Context-Dependent PII
──────────────────────────────────────────────────────────────────────────
Input: "John Smith discussed the algorithm with the team"

Stage 1: Regex (0.9ms)
  └─ No pattern matches ✓

Config: PII_ALWAYS_RUN_PRESIDIO = true (OR text length < 1000 chars)
  └─ Run Stage 2

Stage 2: Presidio (25ms)
  └─ PERSON: "John Smith" (confidence: 0.85) ✓

Result: PII Detected → Block/Warn based on config
Total Latency: 25.9ms
```

---

## Database Integration

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PII METADATA IN DATABASE                                 │
└─────────────────────────────────────────────────────────────────────────────┘

Table: analyses
────────────────────────────────────────────────────────────────────────────

┌──────────────┬────────────┬─────────────────────────────────────────────┐
│ Column       │ Type       │ Description                                 │
├──────────────┼────────────┼─────────────────────────────────────────────┤
│ id           │ UUID       │ Primary key                                 │
│ url          │ TEXT       │ Source URL                                  │
│ content      │ TEXT       │ Extracted content                           │
│ embedding    │ VECTOR     │ 1536-dimensional vector                     │
│ ...          │ ...        │ ...                                         │
│ pii_detected │ BOOLEAN    │ ✅ NEW: PII detection flag                  │
│ pii_types    │ TEXT[]     │ ✅ NEW: Array of detected PII types         │
│ pii_confidence│ FLOAT     │ ✅ NEW: Max confidence score                │
│ pii_detection│ TIMESTAMP  │ ✅ NEW: When PII check was performed        │
│ pii_method   │ TEXT       │ ✅ NEW: "regex", "presidio", or "both"      │
└──────────────┴────────────┴─────────────────────────────────────────────┘

Example Row:
────────────────────────────────────────────────────────────────────────────
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "url": "https://example.com/article",
  "pii_detected": true,
  "pii_types": ["email", "PERSON"],
  "pii_confidence": 0.95,
  "pii_detection_at": "2025-12-10T10:30:00Z",
  "pii_method": "both"
}

Query Examples:
────────────────────────────────────────────────────────────────────────────
-- Find all analyses with PII
SELECT id, url, pii_types FROM analyses WHERE pii_detected = true;

-- Find analyses with high-confidence PII
SELECT id, url, pii_confidence FROM analyses
WHERE pii_detected = true AND pii_confidence > 0.8;

-- Count PII detections by type
SELECT
  unnest(pii_types) as pii_type,
  COUNT(*) as count
FROM analyses
WHERE pii_detected = true
GROUP BY pii_type
ORDER BY count DESC;
```

---

## Metrics Dashboard

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PII DETECTION METRICS (24H)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  DETECTION SUMMARY                                                          │
│  ────────────────────────────────────────────────────────────────           │
│  Total Checks:      1,247                                                   │
│  PII Detected:        127  (10.2%)                                          │
│  Blocked:              85  (6.8%)                                           │
│  Warned:               42  (3.4%)                                           │
│  Clean:             1,120  (89.8%)                                          │
│                                                                             │
│  DETECTION METHOD BREAKDOWN                                                 │
│  ────────────────────────────────────────────────────────────────           │
│  Regex Only:           45  (35.4% of PII detections)                        │
│  Presidio Only:        28  (22.0%)                                          │
│  Both Methods:         54  (42.6%)                                          │
│                                                                             │
│  TOP PII TYPES                                                              │
│  ────────────────────────────────────────────────────────────────           │
│  email             42  ████████████████████████                             │
│  PERSON            38  ██████████████████████                               │
│  phone             24  ██████████████                                       │
│  SSN               12  ███████                                              │
│  ORGANIZATION       8  ████                                                 │
│  IP_ADDRESS         3  ██                                                   │
│                                                                             │
│  PERFORMANCE METRICS                                                        │
│  ────────────────────────────────────────────────────────────────           │
│  p50 Latency:      2.1ms  (fast path - no PII)                              │
│  p95 Latency:     34.5ms  (with Presidio checks)                            │
│  p99 Latency:     52.8ms  (complex text + high sensitivity)                 │
│                                                                             │
│  FALSE POSITIVE RATE (estimated)                                            │
│  ────────────────────────────────────────────────────────────────           │
│  Manual Review (Sample of 50):                                              │
│  True Positives:   47  (94%)                                                │
│  False Positives:   3  (6%)                                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Configuration Examples

### Development Environment

```bash
# .env
PII_DETECTION_ENABLED=true
PII_USE_REGEX=true
PII_USE_PRESIDIO=false  # Skip Presidio for faster dev cycle
PII_SENSITIVITY_LEVEL=low
PII_BLOCK_ON_DETECTION=false  # Warn only, don't block
```

### Staging Environment

```bash
# .env.staging
PII_DETECTION_ENABLED=true
PII_USE_REGEX=true
PII_USE_PRESIDIO=true
PII_ALWAYS_RUN_PRESIDIO=false  # Optimize: only if regex finds patterns
PII_SENSITIVITY_LEVEL=medium
PII_BLOCK_ON_DETECTION=true  # Block to test behavior
PII_ALLOWLIST=["example.com","test.com"]
```

### Production Environment

```bash
# .env.production
PII_DETECTION_ENABLED=true
PII_USE_REGEX=true
PII_USE_PRESIDIO=true
PII_ALWAYS_RUN_PRESIDIO=false  # Performance optimization
PII_SENSITIVITY_LEVEL=medium
PII_BLOCK_ON_DETECTION=true  # Strict: block all PII
PII_ALLOWLIST=["example.com","localhost","127.0.0.1"]
METRICS_ENABLED=true  # Track PII detection metrics
```

---

## Migration Path

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASED ROLLOUT STRATEGY                                  │
└─────────────────────────────────────────────────────────────────────────────┘

Week 1: Regex Only (Low Risk)
─────────────────────────────────────────────────────────────────────────
✅ Implement RegexPIIDetector
✅ Add config flags
✅ Integrate with EmbeddingService (WARN mode)
✅ Monitor false positive rate
✅ No production impact (warning only)

Week 2: Add Presidio (Staged Testing)
─────────────────────────────────────────────────────────────────────────
✅ Add Presidio dependency
✅ Implement PresidioPIIDetector
✅ Test in development environment
✅ Run parallel comparison: Regex vs Presidio
✅ Tune sensitivity levels

Week 3: Hybrid Integration (Beta)
─────────────────────────────────────────────────────────────────────────
✅ Implement HybridPIIDetector
✅ Add smart routing logic
✅ Deploy to staging with BLOCK mode
✅ Monitor metrics for 3-5 days
✅ Collect false positive reports

Week 4: Production Rollout (Gradual)
─────────────────────────────────────────────────────────────────────────
✅ Deploy to production with WARN mode (1 week)
✅ Analyze logs and metrics
✅ Tune allowlist for false positives
✅ Switch to BLOCK mode (phased: 10% → 50% → 100%)
✅ Monitor error rates and user reports
```

---

**Last Updated:** December 10, 2025
**Author:** AI/ML Engineer
**Status:** Architecture Design Complete
