---
name: testing-strategy-builder
description: Use this skill when creating comprehensive testing strategies for applications. Provides test planning templates, coverage targets, test case structures, and guidance for unit, integration, E2E, and performance testing. Ensures robust quality assurance across the development lifecycle.
version: 1.0.0
author: AI Agent Hub
tags: [testing, quality-assurance, test-strategy, automation, coverage]
---

# Testing Strategy Builder

## Overview

This skill provides comprehensive guidance for building effective testing strategies that ensure software quality, reliability, and maintainability. Whether starting from scratch or improving existing test coverage, this framework helps teams design robust testing approaches.

**When to use this skill:**
- Planning testing strategy for new projects or features
- Improving test coverage in existing codebases
- Establishing quality gates and coverage targets
- Designing test automation architecture
- Creating test plans and test cases
- Choosing appropriate testing tools and frameworks
- Implementing continuous testing in CI/CD pipelines

**Bundled Resources:**
- `references/code-examples.md` - Detailed testing code examples
- `templates/test-plan-template.md` - Comprehensive test plan template
- `templates/test-case-template.md` - Test case documentation template
- `checklists/test-coverage-checklist.md` - Coverage verification checklist

## Required Tools

This skill references the following testing tools. Not all are required - the skill will recommend appropriate tools based on your project.

### JavaScript/TypeScript Testing
- **Jest:** Most popular testing framework
  - **Install:** `npm install --save-dev jest @types/jest`
  - **Config:** `npx jest --init`

- **Vitest:** Vite-native testing framework
  - **Install:** `npm install --save-dev vitest`
  - **Config:** Add to vite.config.ts

- **Playwright:** End-to-end testing
  - **Install:** `npm install --save-dev @playwright/test`
  - **Setup:** `npx playwright install`

- **k6:** Performance testing
  - **Install (macOS):** `brew install k6`
  - **Install (Linux):** Download from k6.io
  - **Command:** `k6 run script.js`

### Python Testing
- **pytest:** Standard Python testing framework
  - **Install:** `pip install pytest`
  - **Command:** `pytest`

- **pytest-cov:** Coverage reporting
  - **Install:** `pip install pytest-cov`
  - **Command:** `pytest --cov=.`

- **Locust:** Performance testing
  - **Install:** `pip install locust`
  - **Command:** `locust -f locustfile.py`

### Coverage Tools
- **c8:** JavaScript/TypeScript coverage
  - **Install:** `npm install --save-dev c8`
  - **Command:** `c8 npm test`

- **Istanbul/nyc:** Alternative JS coverage
  - **Install:** `npm install --save-dev nyc`
  - **Command:** `nyc npm test`

### Installation Verification
```bash
# JavaScript/TypeScript
jest --version
vitest --version
playwright --version
k6 version

# Python
pytest --version
locust --version

# Coverage
c8 --version
nyc --version
```

**Note:** The skill will guide you to select tools based on your project framework (React, Vue, FastAPI, Django, etc.) and testing needs.

## Testing Philosophy

### The Testing Trophy 🏆

Modern testing follows the "Testing Trophy" model (evolved from the testing pyramid):

```
         🏆
       /    \
      /  E2E  \         ← Few (critical user journeys)
     /----------\
    / Integration\      ← Many (component interactions)
   /--------------\
  /     Unit       \    ← Most (business logic)
 /------------------\
/  Static Analysis   \  ← Foundation (linting, type checking)
```

**Principles:**
1. **Static Analysis**: Catch syntax errors, type issues, and common bugs before runtime
2. **Unit Tests**: Test individual functions and components in isolation
3. **Integration Tests**: Test how components work together
4. **E2E Tests**: Validate critical user workflows end-to-end

**Balance:** 70% integration, 20% unit, 10% E2E (adjust based on context)

---

## Testing Strategy Framework

### 1. Coverage Targets

**Recommended Targets:**
- **Overall Code Coverage**: 80% minimum
- **Critical Paths**: 95-100% (payment, auth, data mutations)
- **New Features**: 100% coverage requirement
- **Business Logic**: 90%+ coverage
- **UI Components**: 70%+ coverage

**Coverage Types:**
- **Line Coverage**: Percentage of code lines executed
- **Branch Coverage**: Percentage of decision branches taken
- **Function Coverage**: Percentage of functions called
- **Statement Coverage**: Percentage of statements executed

**Important:** Coverage is a metric, not a goal. 100% coverage ≠ bug-free code.

### 2. Test Classification

#### Static Analysis
**Purpose**: Catch errors before runtime
**Tools**: ESLint, Prettier, TypeScript, Pylint, mypy, Ruff
**When to run:** Pre-commit hooks, CI pipeline

#### Unit Tests
**Purpose**: Test isolated business logic
**Tools**: Jest, Vitest, pytest, JUnit
**Characteristics:**
- Fast execution (< 100ms per test)
- No external dependencies (database, API, filesystem)
- Deterministic (same input = same output)
- Test single responsibility

**Coverage Target:** 90%+ for business logic

See `references/code-examples.md` for detailed unit test examples.

#### Integration Tests
**Purpose**: Test component interactions
**Tools:** Testing Library, Supertest, pytest with fixtures
**Characteristics:**
- Test multiple units working together
- May use test databases or mocked external services
- Moderate execution time (< 1s per test)
- Focus on interfaces and contracts

**Coverage Target:** 70%+ for API endpoints and component interactions

See `references/code-examples.md` for API integration test examples.

#### End-to-End (E2E) Tests
**Purpose**: Validate critical user journeys
**Tools:** Playwright, Cypress, Selenium
**Characteristics:**
- Test entire application flow (frontend + backend + database)
- Slow execution (5-30s per test)
- Run against production-like environment
- Focus on business-critical paths

**Coverage Target:** 5-10 critical user journeys

See `references/code-examples.md` for complete E2E test examples.

#### Performance Tests
**Purpose**: Validate system performance under load
**Tools:** k6, Artillery, JMeter, Locust
**Types:**
- **Load Testing**: System behavior under expected load
- **Stress Testing**: Breaking point identification
- **Spike Testing**: Sudden traffic surge handling
- **Soak Testing**: Sustained load over time (memory leaks)

**Coverage Target:** Test all performance-critical endpoints

See `references/code-examples.md` for k6 load test examples.

---

## Test Planning

### 1. Risk-Based Testing

Prioritize testing based on risk assessment:

**High Risk (100% coverage required):**
- Payment processing
- Authentication and authorization
- Data mutations (create, update, delete)
- Security-critical operations
- Compliance-related features

**Medium Risk (80% coverage):**
- Business logic
- Data transformations
- API integrations
- Email/notification systems

**Low Risk (50% coverage):**
- UI styling
- Static content
- Read-only operations
- Non-critical features

### 2. Test Case Design

**Given-When-Then Pattern:**
```
Given [initial context]
When [action occurs]
Then [expected outcome]
```

This pattern keeps tests clear and focused. See `references/code-examples.md` for implementation examples.

### 3. Test Data Management

**Strategies:**
- **Fixtures**: Pre-defined test data in JSON/YAML files
- **Factories**: Generate test data programmatically
- **Seeders**: Populate test database with known data
- **Faker Libraries**: Generate realistic random data

See `references/code-examples.md` for test factory and fixture examples.

---

## Testing Patterns and Best Practices

### 1. AAA Pattern (Arrange-Act-Assert)

Structure tests in three clear phases:
- **Arrange**: Set up test data and context
- **Act**: Perform the action being tested
- **Assert**: Verify expected outcomes

See `references/code-examples.md` for detailed AAA pattern examples.

### 2. Test Isolation

**Each test should be independent:**
- Use fresh test database for each test
- Clean up resources after each test
- Tests don't depend on execution order

See `references/code-examples.md` for test isolation patterns.

### 3. Mocking vs Real Dependencies

**When to Mock:**
- External APIs (payment gateways, third-party services)
- Slow operations (file I/O, network calls)
- Non-deterministic behavior (current time, random values)
- Hard-to-test scenarios (error conditions, edge cases)

**When to Use Real Dependencies:**
- Fast, deterministic operations
- Critical business logic
- Database operations (use test database)
- Internal service interactions

See `references/code-examples.md` for mocking examples.

### 4. Snapshot Testing

**Use for:** UI components, API responses, generated code

**Warning:** Snapshots can become brittle. Use for stable components, not rapidly changing UI.

### 5. Parameterized Tests

Test multiple scenarios with same logic using data tables.

See `references/code-examples.md` for parameterized test patterns.

---

## Continuous Testing

### 1. CI/CD Integration

**Pipeline Stages:**
```yaml
# Example: GitHub Actions
name: Test Pipeline

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: npm ci
      - name: Lint
        run: npm run lint
      - name: Type check
        run: npm run typecheck
      - name: Unit & Integration Tests
        run: npm test -- --coverage
      - name: Upload coverage
        uses: codecov/codecov-action@v3
      - name: E2E Tests
        run: npm run test:e2e
      - name: Performance Tests (on main branch)
        if: github.ref == 'refs/heads/main'
        run: npm run test:performance
```

### 2. Quality Gates

**Block merges/deployments if:**
- Code coverage drops below threshold (e.g., 80%)
- Any tests fail
- Linting errors exist
- Performance regression detected (> 10% slower)
- Security vulnerabilities found

### 3. Test Execution Strategy

**On Every Commit:**
- Static analysis (lint, type check)
- Unit tests
- Fast integration tests (< 5 min total)

**On Pull Request:**
- All tests (unit + integration + E2E)
- Coverage report
- Performance benchmarks

**On Deploy to Staging:**
- Full E2E suite
- Load testing
- Security scans

**On Deploy to Production:**
- Smoke tests (critical paths only)
- Health checks
- Canary deployments with monitoring

---

## Testing Tools Recommendations

### JavaScript/TypeScript

| Category | Tool | Use Case |
|----------|------|----------|
| **Unit/Integration** | Vitest | Fast, Vite-native, modern |
| **Unit/Integration** | Jest | Mature, extensive ecosystem |
| **E2E** | Playwright | Cross-browser, reliable, fast |
| **E2E** | Cypress | Developer-friendly, visual debugging |
| **Component Testing** | Testing Library | User-centric, framework-agnostic |
| **API Testing** | Supertest | HTTP assertions, Express integration |
| **Performance** | k6 | Load testing, scriptable |

### Python

| Category | Tool | Use Case |
|----------|------|----------|
| **Unit/Integration** | pytest | Powerful, extensible, fixtures |
| **API Testing** | httpx + pytest | Async support, modern |
| **E2E** | Playwright (Python) | Browser automation |
| **Performance** | Locust | Load testing, Python-based |
| **Mocking** | unittest.mock | Standard library, reliable |

---

## Common Testing Anti-Patterns

❌ **Testing Implementation Details**
```typescript
// Bad: Testing internal state
expect(component.state.isLoading).toBe(false);

// Good: Testing user-visible behavior
expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
```

❌ **Tests Too Coupled to Code**
```typescript
// Bad: Test breaks when implementation changes
expect(userService.save).toHaveBeenCalledTimes(1);

// Good: Test behavior, not implementation
const user = await db.users.findOne({ email: 'test@example.com' });
expect(user).toBeTruthy();
```

❌ **Flaky Tests**
```typescript
// Bad: Non-deterministic timeout
await waitFor(() => {
  expect(screen.getByText('Success')).toBeInTheDocument();
}, { timeout: 1000 }); // Might fail on slow CI

// Good: Use explicit waits with longer timeout
await screen.findByText('Success', {}, { timeout: 5000 });
```

❌ **Giant Test Cases**
```typescript
// Bad: One test does too much
test('user workflow', async () => {
  // 100 lines testing signup, login, profile update, logout...
});

// Good: Focused tests
test('user can sign up', async () => { /* ... */ });
test('user can login', async () => { /* ... */ });
test('user can update profile', async () => { /* ... */ });
```

---

## Integration with Agents

### Code Quality Reviewer
- Reviews test coverage reports
- Suggests missing test cases
- Validates test quality and structure
- Ensures tests follow patterns from this skill

### Backend System Architect
- Uses test strategy templates when designing services
- Ensures APIs are testable (dependency injection, clear interfaces)
- Plans integration test architecture

### Frontend UI Developer
- Applies component testing patterns
- Uses Testing Library best practices
- Implements E2E tests for user flows

### AI/ML Engineer
- Adapts testing patterns for ML models (data validation, model performance tests)
- Uses performance testing for inference endpoints

---

## Quick Start Checklist

When starting a new project or feature:

- [ ] Define coverage targets (overall, critical paths, new code)
- [ ] Choose testing framework (Jest/Vitest, Playwright, etc.)
- [ ] Set up test infrastructure (test database, fixtures, factories)
- [ ] Create test plan (see `templates/test-plan-template.md`)
- [ ] Implement static analysis (ESLint, TypeScript)
- [ ] Write unit tests for business logic (80%+ coverage)
- [ ] Write integration tests for API endpoints (70%+ coverage)
- [ ] Write E2E tests for critical user journeys (5-10 flows)
- [ ] Configure CI/CD pipeline with quality gates
- [ ] Set up coverage reporting (Codecov, Coveralls)
- [ ] Document testing conventions in project README

**For detailed code examples**: See `references/code-examples.md`

---

## AI/LLM Testing Patterns (v1.1.0)

Testing AI applications requires specialized approaches due to their probabilistic nature.

### Async Timeout Testing

```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_operation_respects_timeout():
    """Test that async operations honor timeout limits."""
    async def slow_operation():
        await asyncio.sleep(10)  # Simulates slow LLM call
        return "result"

    with pytest.raises(asyncio.TimeoutError):
        async with asyncio.timeout(0.1):
            await slow_operation()

@pytest.mark.asyncio
async def test_graceful_degradation_on_timeout():
    """Test fail-open behavior when operation times out."""
    result = await safe_operation_with_fallback(timeout=0.1)
    assert result["status"] == "fallback"
    assert result["error"] == "Operation timed out"
```

### LLM Mock Patterns

```python
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_llm_response():
    """Mock LLM to return predictable structured output."""
    mock = AsyncMock()
    mock.return_value = {
        "content": "Mocked response",
        "confidence": 0.85,
        "tokens_used": 150
    }
    return mock

@pytest.mark.asyncio
async def test_synthesis_with_mocked_llm(mock_llm_response):
    """Test synthesis logic without actual LLM calls."""
    with patch("app.core.model_factory.get_model", return_value=mock_llm_response):
        result = await synthesize_findings(sample_findings)

    assert result["executive_summary"] is not None
    assert mock_llm_response.call_count == 1
```

### Pydantic v2 Model Testing

```python
import pytest
from pydantic import ValidationError

def test_quiz_question_validates_correct_answer():
    """Test that correct_answer must be in options."""
    with pytest.raises(ValidationError) as exc_info:
        QuizQuestion(
            question="What is 2+2?",
            options=["3", "4", "5"],
            correct_answer="6",  # Not in options!
            explanation="Basic arithmetic"
        )

    assert "correct_answer" in str(exc_info.value)
    assert "must be one of" in str(exc_info.value)

def test_quiz_question_accepts_valid_answer():
    """Test that valid answers pass validation."""
    q = QuizQuestion(
        question="What is 2+2?",
        options=["3", "4", "5"],
        correct_answer="4",  # Valid!
        explanation="Basic arithmetic"
    )
    assert q.correct_answer == "4"
```

### Template Rendering Tests

```python
from jinja2 import Environment, FileSystemLoader

@pytest.fixture
def jinja_env():
    return Environment(loader=FileSystemLoader("templates/"))

def test_template_handles_empty_tldr(jinja_env):
    """Template renders without crashing when tldr is empty."""
    template = jinja_env.get_template("artifact.j2")
    result = template.render(aggregated_insights={"tldr": {}})
    assert "TL;DR" not in result  # Section skipped gracefully

def test_template_handles_missing_nested_field(jinja_env):
    """Template handles None in nested objects."""
    template = jinja_env.get_template("artifact.j2")
    result = template.render(aggregated_insights={
        "tldr": {"summary": None, "key_takeaways": []}
    })
    # Should not crash, should handle gracefully
    assert isinstance(result, str)
```

### LLM-as-Judge Evaluator Testing

```python
@pytest.mark.asyncio
async def test_quality_evaluator_returns_normalized_score():
    """Quality scores should be normalized 0.0-1.0."""
    evaluator = create_quality_evaluator("relevance")

    # Mock the LLM to return a score
    with patch_evaluator_llm(return_score=8):  # 8/10
        result = await evaluator.aevaluate_strings(
            input="Test input",
            prediction="Test output"
        )

    assert 0.0 <= result["score"] <= 1.0
    assert result["score"] == 0.8  # 8/10 normalized

@pytest.mark.asyncio
async def test_quality_gate_fails_below_threshold():
    """Quality gate should fail when avg score < threshold."""
    with patch_quality_scores({"relevance": 0.5, "depth": 0.4, "coherence": 0.5}):
        result = await quality_gate_node(sample_state)

    assert result["quality_gate_passed"] is False
    assert result["quality_gate_avg_score"] < 0.7
```

### Edge Case Identification Strategy

When testing LLM integrations, always test these edge cases:
- **Empty inputs:** What happens with empty strings or None?
- **Very long inputs:** Does truncation work correctly?
- **Timeout scenarios:** Does fail-open work?
- **Partial responses:** What if LLM returns 90% complete?
- **Invalid structured output:** What if schema validation fails?
- **Division by zero:** What if averaging over empty list?
- **Nested null access:** What if parent object exists but child is None?

---

**Skill Version**: 1.1.0
**Last Updated**: 2025-12-14
**Maintained by**: AI Agent Hub Team
