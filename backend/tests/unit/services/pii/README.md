# PII Detection Service Unit Tests

## Overview

Comprehensive unit test suite for the PII (Personally Identifiable Information) detection service, created as part of Issue #220 - PII/Safety Guardrails.

## Test Statistics

- **Total Tests:** 56
- **Test File:** `test_detector.py`
- **Lines of Code:** ~944
- **Test Classes:** 6
- **All Tests Passing:** ✅ 56/56

## Test Structure

### 1. TestPIIDetector (29 tests)
Main detection functionality testing:

**Email Detection (3 tests)**
- Standard email addresses
- Multiple emails in one text
- Emails with special characters (dots, underscores, plus signs)

**Phone Number Detection (2 tests)**
- US phone numbers (various formats: `(555) 123-4567`, `555-123-4567`, `+1 555-123-4567`)
- International phone numbers (`+44`, `+49`, `+33`, `+81` formats)

**SSN Detection (3 tests)**
- Standard format with dashes (`123-45-6789`)
- Format with spaces (`123 45 6789`)
- Format without separators (`123456789`)

**Credit Card Detection (4 tests)**
- Visa (16 digits, starts with 4)
- Mastercard (16 digits, starts with 51-55)
- American Express (15 digits, starts with 34/37)
- Discover (16 digits, starts with 6011/65)

**IP Address Detection (2 tests)**
- IPv4 addresses (`192.168.1.1`, `10.0.0.1`, `8.8.8.8`)
- IPv6 addresses (full format)

**API Key Detection (3 tests)**
- AWS access keys (`AKIA...`, `ASIA...`, `ACCA...`, `ABIA...`)
- GitHub personal access tokens (`ghp_...`, `gho_...`, `ghu_...`)
- Stripe API keys (`sk_live_...`, `sk_test_...`, `pk_live_...`)

**Negative Tests (4 tests)**
- Clean technical documentation (no false positives)
- Code samples (no false positives)
- Random numbers (no false positives)
- Version numbers (no false positives)

**Configuration Tests (4 tests)**
- Disabled detector returns no PII
- LOW sensitivity only detects emails
- MEDIUM sensitivity includes email, phone, SSN, credit cards
- HIGH sensitivity includes all patterns + API keys

**Batch Processing Tests (2 tests)**
- Batch scanning returns correct counts
- Multiple PII types in single text

**Privacy Tests (2 tests)**
- Metadata doesn't contain actual PII values
- PIIResult never stores actual PII values

### 2. TestPIIPatterns (10 tests)
Individual regex pattern validation:

- Email pattern validation (valid and invalid formats)
- SSN pattern validation (with/without dashes)
- Credit card format validation (not Luhn checksum)
- IPv4 pattern validation (valid and invalid)
- AWS key pattern validation
- GitHub token pattern validation
- Stripe key pattern validation

### 3. TestPIISensitivity (4 tests)
Sensitivity level configuration:

- LOW: Only email patterns active
- MEDIUM: Email, phone, SSN, credit card patterns
- HIGH: All patterns including IP addresses and API keys
- MAXIMUM: Same as HIGH (reserved for future NER integration)

### 4. TestPIIPrivacy (3 tests)
Privacy-preserving guarantees:

- Detector never logs actual PII values
- Match objects only store offsets (start/end), not values
- Metadata structure is safe (no PII leakage)

### 5. TestPIIBatch (5 tests)
Batch scanning operations:

- Empty list handling
- All clean chunks
- All flagged chunks
- Mixed clean and flagged chunks
- Order preservation

### 6. TestPIIEdgeCases (5 tests)
Edge cases and boundary conditions:

- Empty string handling
- Whitespace-only string handling
- Very long text (10,000+ words)
- Unicode text handling
- Mixed case pattern matching

## Test Coverage

### PII Types Covered
1. ✅ EMAIL - Standard email addresses
2. ✅ PHONE_US - US phone numbers
3. ✅ PHONE_INTL - International phone numbers
4. ✅ SSN - Social Security Numbers
5. ✅ CREDIT_CARD - Visa, Mastercard, Amex, Discover
6. ✅ IPV4 - IPv4 addresses
7. ✅ IPV6 - IPv6 addresses
8. ✅ AWS_KEY - AWS access keys
9. ✅ GITHUB_TOKEN - GitHub personal access tokens
10. ✅ STRIPE_KEY - Stripe API keys

### Sensitivity Levels Covered
1. ✅ LOW - Basic detection (email only)
2. ✅ MEDIUM - Standard detection (email, phone, SSN, credit cards)
3. ✅ HIGH - Full detection (all patterns including API keys)
4. ✅ MAXIMUM - Same as HIGH (reserved for future Presidio NER)

## Running Tests

### Run All PII Tests
```bash
cd backend
poetry run pytest tests/unit/services/pii/test_detector.py -v
```

### Run Specific Test Class
```bash
# Run only email detection tests
poetry run pytest tests/unit/services/pii/test_detector.py::TestPIIDetector -v

# Run only pattern validation tests
poetry run pytest tests/unit/services/pii/test_detector.py::TestPIIPatterns -v
```

### Run Single Test
```bash
poetry run pytest tests/unit/services/pii/test_detector.py::TestPIIDetector::test_detects_email -v
```

### Run with Coverage
```bash
poetry run pytest tests/unit/services/pii/test_detector.py --cov=app.services.pii --cov-report=term-missing
```

## Test Design Principles

### 1. Privacy-First
- Tests verify that actual PII values are NEVER stored or logged
- Match objects only contain offsets (start/end positions)
- Metadata is safe for logging/storage

### 2. Fast Execution
- No external dependencies (no API calls, no database)
- Pure unit tests (no integration)
- Average execution time: ~0.21 seconds for 56 tests

### 3. Comprehensive Coverage
- All PII types tested
- All sensitivity levels tested
- Positive and negative cases
- Edge cases and boundary conditions

### 4. Following Existing Patterns
- Uses pytest (same as other backend tests)
- Follows naming conventions (`test_*.py`, `Test*` classes)
- Similar structure to existing service tests

## Architecture Reference

Based on:
- `docs/issues/220-pii-safety-guardrails/ARCHITECTURE_DESIGN.md`
- `docs/issues/220-pii-safety/QUICK_REFERENCE.md`
- `app/services/pii/types.py`

## Mock Implementation

The test file includes a mock `PIIDetector` implementation that:
1. Matches the architecture specification
2. Implements all required patterns
3. Supports all sensitivity levels
4. Never stores actual PII values

**Note:** This mock will be replaced with the actual implementation from `app/services/pii/detector.py` once created.

## Test Execution Results

```
============================== 56 passed in 0.21s ===============================
```

All tests passing! 🎉

## Next Steps

1. Implement actual `app/services/pii/patterns.py` with production regex patterns
2. Implement actual `app/services/pii/detector.py` with the PIIDetector class
3. Integrate with embedding pipeline (as per architecture doc)
4. Add integration tests with real database
5. Add performance benchmarks

## Author

Backend System Architect
Issue: #220 - PII/Safety Guardrails
Date: December 10, 2025
