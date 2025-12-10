# PII Detection Quick Start

## 1. Basic Usage

```python
from app.services.pii import PIIDetector, SensitivityLevel

# Create detector
detector = PIIDetector(
    sensitivity=SensitivityLevel.MEDIUM,
    enabled=True
)

# Scan text
result = detector.scan("Email me at user@example.com")

# Check result (NO actual PII values in result)
if result.has_pii:
    print(f"PII detected: {result.types}")
    print(f"Count: {result.match_count}")
```

## 2. Singleton Pattern

```python
from app.services.pii import get_pii_detector

# Get global instance (auto-configured)
detector = get_pii_detector()
result = detector.scan(text)
```

## 3. Batch Scanning

```python
chunks = ["text1", "email@test.com", "text3"]
results, clean, flagged = detector.scan_chunks(chunks)
print(f"Clean: {clean}, Flagged: {flagged}")
```

## 4. Metadata Export

```python
result = detector.scan(text)
metadata = result.to_metadata()
# Returns: {'pii_flag': bool, 'pii_types': list, 'pii_count': int}
# NEVER includes actual PII values
```

## 5. Configuration

```python
# In app/core/config.py
PII_SCREENING_ENABLED: bool = False
PII_SENSITIVITY_LEVEL: str = "medium"  # low|medium|high|maximum
PII_ACTION: str = "flag"  # flag|reject
```

## 6. Sensitivity Levels

- **LOW**: Email only
- **MEDIUM**: Email, phone, SSN, credit cards
- **HIGH**: All regex patterns + API keys
- **MAXIMUM**: (Future) + Presidio NER

## 7. Detected PII Types

```python
from app.services.pii import PIIType

PIIType.EMAIL           # Email addresses
PIIType.PHONE_US        # US phone numbers
PIIType.PHONE_INTL      # International phone
PIIType.SSN             # Social Security Numbers
PIIType.CREDIT_CARD     # Credit cards (Visa, MC, Amex, etc.)
PIIType.IPV4 / IPV6     # IP addresses
PIIType.AWS_KEY         # AWS access keys
PIIType.GITHUB_TOKEN    # GitHub tokens
PIIType.STRIPE_KEY      # Stripe API keys
```

## 8. Privacy Guarantee

**NEVER stored or logged:**
- Actual PII values
- Extracted text
- Redacted versions

**Only stored:**
- Boolean flags (has_pii)
- Type enums (email, phone, etc.)
- Match counts
- Character positions (for debugging)

## 9. Integration Example

```python
# In chunking service
from app.services.pii import get_pii_detector

detector = get_pii_detector()

for chunk in chunks:
    # Scan before embedding
    pii_result = detector.scan(chunk.content)
    
    # Add metadata (no values)
    chunk.metadata["pii"] = pii_result.to_metadata()
    
    # Optionally reject
    if pii_result.should_reject:
        logger.warning("chunk_rejected_pii", chunk_id=chunk.id)
        continue
```

## 10. Testing

```bash
# Test patterns
cd backend
python3 -c "
from app.services.pii import PIIDetector, SensitivityLevel
detector = PIIDetector(sensitivity=SensitivityLevel.HIGH, enabled=True)
result = detector.scan('Test: user@example.com, 555-123-4567')
print(f'Detected: {result.types}, Count: {result.match_count}')
"
```

---

**Full Documentation**: See `README.md` in this directory.
**Source Files**: `types.py`, `patterns.py`, `detector.py`, `__init__.py`
