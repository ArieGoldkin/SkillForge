# Issue #253: Real-World Data Collection from Langfuse & GitHub

**Sprint**: 12 (Evaluation Dataset)
**Points**: 8
**Status**: Completed

## Objective

Collect 50+ real-world examples from production Langfuse traces and GitHub issues to achieve 70%+ real-world data ratio in the evaluation dataset.

## Deliverables

### 1. PII Anonymizer Module (`app/evaluation/ingestion/pii_anonymizer.py`)

A production-safe PII anonymization system that:
- Detects emails, phone numbers, SSNs, credit cards, IP addresses, and API keys
- Uses deterministic placeholders (`[EMAIL_1]`, `[PHONE_2]`) for consistency
- Preserves allowlisted safe patterns (example.com, private IPs)
- Supports sensitivity levels (LOW, MEDIUM, HIGH)
- Provides batch processing for multiple texts

**Key Features**:
```python
from app.evaluation.ingestion import PIIAnonymizer, get_anonymizer

# Get cached anonymizer
anonymizer = get_anonymizer()

# Anonymize content
result = anonymizer.anonymize("Contact john@corp.com at 555-123-4567")
# result.text: "Contact [EMAIL_1] at [PHONE_1]"
# result.has_pii: True
# result.pii_count: 2
```

### 2. GitHub Issue Importer (`app/evaluation/ingestion/github_importer.py`)

A GitHub issue collection system that:
- Fetches issues with rate limiting (4000 req/hour with token bucket)
- Infers agent types from content keywords and labels
- Infers technical domains from repository and content
- Estimates difficulty from issue complexity
- Converts to v2.0 dataset schema

**Key Features**:
```python
from app.evaluation.ingestion import GitHubImporter, GitHubImportConfig

config = GitHubImportConfig(
    owner="langchain-ai",
    repo="langchain",
    min_reactions=10,
    labels=["bug", "documentation"],
    limit=50
)

importer = GitHubImporter()
examples = await importer.import_issues(config)
importer.save_dataset(examples, "datasets/drafts/github_langchain.json")
```

### 3. Enhanced Langfuse Extractor

Enhanced the existing extractor with:
- **Domain Inference**: Maps content keywords and agent types to technical domains
- **PII Integration**: Automatically anonymizes extracted content
- **Batch Extraction**: `extract_all_agents()` for balanced 8-agent coverage
- **Confidence Bands**: `extract_by_confidence_bands()` for high/medium/low grouping

**New Methods**:
```python
from app.evaluation.ingestion import LangfuseExtractor

extractor = LangfuseExtractor()

# Extract balanced examples for all 8 agents
examples = extractor.extract_all_agents(
    project_name="skillforge-prod",
    examples_per_agent=5
)

# Extract by confidence bands
bands = extractor.extract_by_confidence_bands(
    project_name="skillforge-prod",
    examples_per_band=10
)
# Returns: {"high": [...], "medium": [...], "low": [...]}
```

## Domain Mappings

| Agent Type | Primary Domains |
|------------|-----------------|
| tech_comparator | backend, frontend, llm-orchestration |
| security_auditor | security |
| implementation_planner | backend, frontend, agent-systems |
| performance_analyst | data-layer, devops, backend |
| code_quality_critic | backend, frontend |
| dependency_mapper | llm-orchestration, agent-systems |
| trend_validator | machine-learning, devops |
| integration_feasibility | llm-orchestration, agent-systems, backend |

## Test Coverage

| Module | Tests | Status |
|--------|-------|--------|
| PII Anonymizer | 32 | All passing |
| GitHub Importer | 27 | All passing |
| Langfuse Extractor | 41 (23 new) | All passing |
| Validation | 13 | All passing |
| **Total** | **113** | **All passing** |

## Files Modified/Created

### New Files
- `app/evaluation/ingestion/pii_anonymizer.py` (393 lines)
- `app/evaluation/ingestion/github_importer.py` (693 lines)
- `tests/unit/evaluation/test_pii_anonymizer.py` (410 lines)
- `tests/unit/evaluation/test_github_importer.py` (509 lines)

### Modified Files
- `app/evaluation/ingestion/__init__.py` - Added exports
- `app/evaluation/ingestion/langfuse_extractor.py` - Enhanced with domain/PII
- `tests/unit/evaluation/test_langfuse_extractor.py` - Added 23 new tests

## Verification Checklist

- [x] PII Anonymizer detects all PII types (email, phone, SSN, credit card, IP, API keys)
- [x] PII Anonymizer preserves allowlisted patterns
- [x] GitHub Importer respects rate limits
- [x] GitHub Importer infers agents from keywords and labels
- [x] Langfuse Extractor anonymizes content before storage
- [x] Langfuse Extractor includes domain in metadata
- [x] All 113 unit tests passing
- [x] All lint checks passing (ruff format, ruff check, mypy)
- [x] v2.0 schema compatibility maintained

## Commits

1. `eafc685` - feat(#253): add PII anonymizer and GitHub importer for data collection
2. `4d80017` - feat(#253): enhance Langfuse extractor with domain inference and PII integration
