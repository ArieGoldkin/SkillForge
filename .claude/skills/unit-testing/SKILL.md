---
name: unit-testing
description: Unit testing patterns and best practices. Use when writing isolated unit tests, implementing AAA pattern, designing test isolation, or setting coverage targets for business logic.
---

# Unit Testing

Test isolated business logic with fast, deterministic tests.

## When to Use

- Testing pure functions
- Business logic isolation
- Fast feedback loops
- High coverage targets

## AAA Pattern (Arrange-Act-Assert)

```typescript
describe('calculateDiscount', () => {
  test('applies 10% discount for orders over $100', () => {
    // Arrange
    const order = { items: [{ price: 150 }] };

    // Act
    const result = calculateDiscount(order);

    // Assert
    expect(result).toBe(15);
  });
});
```

## Test Isolation

```typescript
describe('UserService', () => {
  let service: UserService;
  let mockRepo: MockRepository;

  beforeEach(() => {
    // Fresh instances per test
    mockRepo = createMockRepository();
    service = new UserService(mockRepo);
  });

  afterEach(() => {
    // Clean up
    jest.clearAllMocks();
  });
});
```

## Coverage Targets

| Area | Target |
|------|--------|
| Business logic | 90%+ |
| Critical paths | 100% |
| New features | 100% |
| Utilities | 80%+ |

## Parameterized Tests

```typescript
describe('isValidEmail', () => {
  test.each([
    ['test@example.com', true],
    ['invalid', false],
    ['@missing.com', false],
    ['user@domain.co.uk', true],
  ])('isValidEmail(%s) returns %s', (email, expected) => {
    expect(isValidEmail(email)).toBe(expected);
  });
});
```

## Python Example

```python
import pytest

class TestCalculateDiscount:
    def test_applies_discount_over_threshold(self):
        # Arrange
        order = Order(total=150)

        # Act
        discount = calculate_discount(order)

        # Assert
        assert discount == 15

    @pytest.mark.parametrize("total,expected", [
        (100, 0),
        (101, 10.1),
        (200, 20),
    ])
    def test_discount_thresholds(self, total, expected):
        order = Order(total=total)
        assert calculate_discount(order) == expected
```

## Key Decisions

| Decision | Recommendation |
|----------|----------------|
| Framework | Vitest (modern), Jest (mature), pytest |
| Execution | < 100ms per test |
| Dependencies | None (mock everything external) |
| Coverage tool | c8, nyc, pytest-cov |

## Common Mistakes

- Testing implementation, not behavior
- Slow tests (external calls)
- Shared state between tests
- Over-mocking (testing mocks not code)

## Related Skills

- `integration-testing` - Testing interactions
- `msw-mocking` - Network mocking
- `test-data-management` - Fixtures and factories
