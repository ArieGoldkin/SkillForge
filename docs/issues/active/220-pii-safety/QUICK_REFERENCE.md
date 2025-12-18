# PII Detection Quick Reference

**Issue:** #220 - PII/Safety Guardrails
**For:** Backend Developers implementing PII detection
**Last Updated:** December 10, 2025

---

## TL;DR - What to Use

```python
# Recommended: Hybrid approach (Regex + Presidio)
from app.services.pii.hybrid_detector import HybridPIIDetector, SensitivityLevel

detector = HybridPIIDetector(
    use_regex=True,
    use_presidio=True,
    sensitivity=SensitivityLevel.MEDIUM,
)

result = detector.detect("Contact john@example.com for details")
if result.has_pii:
    print(f"PII detected: {result.pii_types}")
    # Handle blocking or warning based on config
```

---

## Quick Decision Guide

```
┌─────────────────────────────────────────────────────────┐
│  Need ultra-fast detection (< 5ms)?                     │
│  Only care about email/phone/SSN?                       │
│  → Use Regex Only                                       │
├─────────────────────────────────────────────────────────┤
│  Need names, organizations, locations?                  │
│  Already using spaCy in project?                        │
│  → Use spaCy NER                                        │
├─────────────────────────────────────────────────────────┤
│  Production deployment with compliance (GDPR/HIPAA)?    │
│  Need all PII types + high accuracy?                    │
│  → Use Presidio                                         │
├─────────────────────────────────────────────────────────┤
│  Want best of both worlds?                              │
│  Need fast path + high accuracy?                        │
│  → Use Hybrid (RECOMMENDED) ⭐                          │
└─────────────────────────────────────────────────────────┘
```

---

## Installation

### Regex Only (Zero Dependencies)
```bash
# No installation needed - uses Python's built-in `re` module
```

### spaCy NER
```bash
poetry add spacy
poetry run python -m spacy download en_core_web_sm
```

### Presidio
```bash
poetry add presidio-analyzer presidio-anonymizer
poetry add spacy
poetry run python -m spacy download en_core_web_sm
```

### Hybrid (Recommended)
```bash
# Same as Presidio
poetry add presidio-analyzer presidio-anonymizer spacy
poetry run python -m spacy download en_core_web_sm
```

---

## Configuration Examples

### Development (Fast Iteration)
```bash
# .env
PII_DETECTION_ENABLED=true
PII_USE_REGEX=true
PII_USE_PRESIDIO=false  # Skip for speed
PII_SENSITIVITY_LEVEL=low
PII_BLOCK_ON_DETECTION=false  # Warn only
```

### Staging (Testing)
```bash
# .env.staging
PII_DETECTION_ENABLED=true
PII_USE_REGEX=true
PII_USE_PRESIDIO=true
PII_ALWAYS_RUN_PRESIDIO=false
PII_SENSITIVITY_LEVEL=medium
PII_BLOCK_ON_DETECTION=true  # Test blocking
PII_ALLOWLIST=["example.com","test.com"]
```

### Production (Full Protection)
```bash
# .env.production
PII_DETECTION_ENABLED=true
PII_USE_REGEX=true
PII_USE_PRESIDIO=true
PII_ALWAYS_RUN_PRESIDIO=false  # Optimize
PII_SENSITIVITY_LEVEL=medium
PII_BLOCK_ON_DETECTION=true
PII_ALLOWLIST=["example.com","localhost","127.0.0.1"]
METRICS_ENABLED=true
```

---

## Code Examples

### 1. Regex Detector (Fastest)

```python
from app.services.pii.regex_detector import RegexPIIDetector, PIIType

# Initialize
detector = RegexPIIDetector(
    enabled_patterns=[PIIType.EMAIL, PIIType.PHONE, PIIType.SSN]
)

# Detect
result = detector.detect("Email: john@example.com, Phone: 555-1234")

# Check results
if result.has_pii:
    print(f"Found {result.match_count} PII instances")
    print(f"Types: {result.pii_types}")
    print(f"Confidence: {result.confidence_score}")
```

### 2. Presidio Detector (Most Accurate)

```python
from app.services.pii.presidio_detector import (
    PresidioPIIDetector,
    SensitivityLevel,
)

# Initialize
detector = PresidioPIIDetector(
    sensitivity=SensitivityLevel.MEDIUM,
    enabled_entities=["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER"],
)

# Detect
result = detector.detect("John Smith called from 555-1234")

# Check results
if result.has_pii:
    print(f"Entity types: {result.entity_types}")
    print(f"Max confidence: {result.max_confidence}")
```

### 3. Hybrid Detector (Recommended)

```python
from app.services.pii.hybrid_detector import (
    HybridPIIDetector,
    SensitivityLevel,
)

# Initialize
detector = HybridPIIDetector(
    use_regex=True,
    use_presidio=True,
    sensitivity=SensitivityLevel.MEDIUM,
)

# Detect
text = "Contact John at john@example.com or 555-1234"
result = detector.detect(text)

# Check results
if result.has_pii:
    print(f"PII types: {result.pii_types}")
    print(f"Regex matches: {result.match_count_regex}")
    print(f"Presidio matches: {result.match_count_presidio}")
    print(f"Detection method: {result.detection_method}")
```

---

## Integration with Embedding Service

### Option 1: Block on Detection (Recommended)

```python
# backend/app/services/embeddings.py

from app.core.exceptions import PIIDetectedError
from app.services.pii.hybrid_detector import HybridPIIDetector

class EmbeddingService:
    def __init__(self):
        # ... existing init ...
        self._pii_detector = HybridPIIDetector() if settings.PII_DETECTION_ENABLED else None

    async def generate_embedding(self, text: str) -> EmbeddingVector:
        # PII check
        if self._pii_detector:
            pii_result = self._pii_detector.detect(text)
            if pii_result.has_pii:
                logger.warning(
                    "pii_detected",
                    pii_types=pii_result.pii_types,
                    confidence=pii_result.max_confidence,
                )
                if settings.PII_BLOCK_ON_DETECTION:
                    raise PIIDetectedError(pii_types=pii_result.pii_types)

        # ... continue with embedding generation ...
```

### Option 2: Flag in Database (Non-Blocking)

```python
# backend/app/workflows/tasks/generate_embedding.py

async def generate_embedding_task(state: AnalysisState) -> dict:
    embedding_service = EmbeddingService()
    pii_detector = HybridPIIDetector()

    text = state["extracted_content"]
    pii_result = pii_detector.detect(text)

    # Generate embedding regardless
    embedding = await embedding_service.generate_embedding(
        text,
        skip_pii_check=True,  # Already checked
    )

    # Store PII flags
    return {
        "embedding": embedding,
        "pii_detected": pii_result.has_pii,
        "pii_types": pii_result.pii_types,
        "pii_confidence": pii_result.max_confidence,
    }
```

---

## Performance Optimization Tips

### 1. Use Fast Path for Clean Content (90% of cases)

```python
# Set this to false for best performance
PII_ALWAYS_RUN_PRESIDIO=false

# This skips Presidio if regex finds nothing
# Latency: 0.8ms instead of 28ms
```

### 2. Tune Batch Processing

```python
# For batch embedding generation
texts = ["text1", "text2", ...]

# Check PII once before batching
pii_results = [detector.detect(text) for text in texts]
clean_texts = [
    text for text, result in zip(texts, pii_results)
    if not result.has_pii
]

# Only embed clean texts
embeddings = await embedding_service.generate_embeddings_batch(clean_texts)
```

### 3. Use Allowlist for Common False Positives

```python
# .env
PII_ALLOWLIST=["example.com","localhost","test.com","John Doe"]

# Or in code
detector = PresidioPIIDetector(sensitivity=SensitivityLevel.MEDIUM)
result = detector.detect_with_allowlist(
    text="Email john@example.com",
    allowlist=["example.com"],
)
# Result: has_pii = False (example.com is allowed)
```

---

## Common Pitfalls & Solutions

### Pitfall 1: Logging Actual PII

❌ **BAD:**
```python
logger.warning(f"PII detected: {matched_email}")
```

✅ **GOOD:**
```python
logger.warning(
    "pii_detected",
    pii_types=["email"],
    confidence=0.95,
    text_length=len(text),
)
```

### Pitfall 2: Blocking Too Aggressively

❌ **BAD:**
```python
# High sensitivity + blocking = too many false positives
PII_SENSITIVITY_LEVEL=high
PII_BLOCK_ON_DETECTION=true
```

✅ **GOOD:**
```python
# Start with medium sensitivity, tune based on logs
PII_SENSITIVITY_LEVEL=medium
PII_BLOCK_ON_DETECTION=true
PII_ALLOWLIST=["example.com","test.com"]  # Add known false positives
```

### Pitfall 3: Not Handling Detection Errors

❌ **BAD:**
```python
result = detector.detect(text)  # Might raise exception
if result.has_pii:
    raise PIIDetectedError()
```

✅ **GOOD:**
```python
try:
    result = detector.detect(text)
    if result.has_pii:
        raise PIIDetectedError(pii_types=result.pii_types)
except Exception as e:
    logger.exception("pii_detection_failed", error=str(e))
    # Fall back to allowing text (or blocking, depending on policy)
    if settings.PII_FAIL_CLOSED:
        raise PIIDetectedError(pii_types=["unknown"])
```

---

## Testing Checklist

### Unit Tests

```python
# backend/tests/unit/services/pii/test_hybrid_detector.py

def test_detect_email():
    detector = HybridPIIDetector()
    result = detector.detect("Email: john@example.com")
    assert result.has_pii
    assert "email" in result.pii_types

def test_detect_phone():
    detector = HybridPIIDetector()
    result = detector.detect("Call 555-123-4567")
    assert result.has_pii
    assert "phone" in result.pii_types

def test_detect_person_name():
    detector = HybridPIIDetector()
    result = detector.detect("John Smith works here")
    assert result.has_pii
    assert "PERSON" in result.pii_types

def test_no_pii():
    detector = HybridPIIDetector()
    result = detector.detect("This is a technical article")
    assert not result.has_pii

def test_allowlist():
    detector = PresidioPIIDetector()
    result = detector.detect_with_allowlist(
        "Email: test@example.com",
        allowlist=["example.com"],
    )
    assert not result.has_pii  # example.com is allowed
```

### Integration Tests

```python
# backend/tests/integration/services/test_embedding_with_pii.py

async def test_embedding_blocks_pii():
    service = EmbeddingService()
    with pytest.raises(PIIDetectedError) as exc_info:
        await service.generate_embedding("Email: real@gmail.com")

    assert "email" in exc_info.value.pii_types

async def test_embedding_allows_clean_text():
    service = EmbeddingService()
    embedding = await service.generate_embedding("Clean technical content")
    assert len(embedding) == 1536  # Should succeed
```

---

## Monitoring & Metrics

### Key Metrics to Track

```python
# backend/app/services/metrics.py

class MetricsService:
    def record_pii_detection(
        self,
        pii_types: list[str],
        detection_method: str,
        blocked: bool,
    ):
        logger.info(
            "metric.pii_detection",
            pii_types=pii_types,
            detection_method=detection_method,  # "regex_only", "presidio_only", "both"
            blocked=blocked,
            timestamp=time.time(),
        )
```

### CloudWatch Queries

```sql
-- Count PII detections by type (last 24h)
fields @timestamp, pii_types
| filter event = "pii_detected"
| stats count() by pii_types

-- Average detection latency
fields @timestamp, detection_latency_ms
| filter event = "pii_detected"
| stats avg(detection_latency_ms), max(detection_latency_ms)

-- False positive rate (manual review needed)
fields @timestamp, pii_types, confidence
| filter event = "pii_detected" AND confidence < 0.7
| count
```

---

## Sensitivity Level Guide

| Level | Threshold | When to Use | Trade-offs |
|-------|-----------|-------------|------------|
| **LOW** | 0.7 | Public content, tutorials | Fewer false positives, may miss some PII |
| **MEDIUM** | 0.5 | General use, mixed content | ⭐ Recommended - balanced |
| **HIGH** | 0.3 | User data, compliance | Catches more PII, more false positives |

### Example: Sensitivity Impact

```python
# Same text, different sensitivity
text = "John works at Microsoft"

# Low sensitivity (0.7)
detector = PresidioPIIDetector(sensitivity=SensitivityLevel.LOW)
result = detector.detect(text)
# Result: has_pii = False (confidence 0.65 < 0.7 threshold)

# Medium sensitivity (0.5)
detector = PresidioPIIDetector(sensitivity=SensitivityLevel.MEDIUM)
result = detector.detect(text)
# Result: has_pii = True (confidence 0.65 > 0.5 threshold)

# High sensitivity (0.3)
detector = PresidioPIIDetector(sensitivity=SensitivityLevel.HIGH)
result = detector.detect(text)
# Result: has_pii = True (confidence 0.65 > 0.3 threshold)
```

---

## Troubleshooting

### Issue: Too Many False Positives

**Symptoms:** Blocking too much clean content

**Solutions:**
1. Lower sensitivity: `HIGH` → `MEDIUM` → `LOW`
2. Add to allowlist: `PII_ALLOWLIST=["example.com","localhost"]`
3. Switch to WARN mode temporarily: `PII_BLOCK_ON_DETECTION=false`
4. Review logs for common patterns, add to allowlist

### Issue: Missing PII (False Negatives)

**Symptoms:** PII getting through detection

**Solutions:**
1. Increase sensitivity: `LOW` → `MEDIUM` → `HIGH`
2. Enable both detectors: `PII_USE_REGEX=true` + `PII_USE_PRESIDIO=true`
3. Add custom regex patterns (if specific to your domain)
4. Always run Presidio: `PII_ALWAYS_RUN_PRESIDIO=true`

### Issue: Slow Performance

**Symptoms:** > 100ms p95 latency

**Solutions:**
1. Disable `PII_ALWAYS_RUN_PRESIDIO` (run only if regex finds patterns)
2. Use smaller spaCy model: `en_core_web_sm` instead of `en_core_web_lg`
3. Cache detector instances (don't recreate per request)
4. Consider regex-only mode for non-critical paths

---

## Production Rollout Checklist

- [ ] Add PII detection dependencies to `pyproject.toml`
- [ ] Download spaCy model: `python -m spacy download en_core_web_sm`
- [ ] Configure environment variables in `.env.production`
- [ ] Add allowlist for known false positives
- [ ] Start with `PII_BLOCK_ON_DETECTION=false` (warn only)
- [ ] Monitor logs for 7 days, collect metrics
- [ ] Tune allowlist based on false positives
- [ ] Gradually enable blocking: 10% → 50% → 100%
- [ ] Set up CloudWatch alerts for PII detection spikes
- [ ] Document false positive handling process
- [ ] Train team on PII incident response

---

## Support & Resources

- **Full Research:** `/docs/issues/220-pii-safety/PII_DETECTION_RESEARCH.md`
- **Architecture:** `/docs/issues/220-pii-safety/ARCHITECTURE_DIAGRAM.md`
- **Comparison Table:** `/docs/issues/220-pii-safety/COMPARISON_TABLE.md`
- **Presidio Docs:** https://microsoft.github.io/presidio/
- **spaCy NER Guide:** https://spacy.io/usage/linguistic-features#named-entities

---

**Last Updated:** December 10, 2025
**Author:** AI/ML Engineer
**Questions?** Slack: #backend-platform
