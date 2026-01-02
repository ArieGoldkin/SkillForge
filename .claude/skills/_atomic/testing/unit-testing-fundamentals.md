---
name: unit-testing-fundamentals
description: Core unit testing patterns - AAA, isolation, test design
version: 1.0.0
tags: [testing, unit-tests, patterns]
size: atomic
domain: testing
---

# Unit Testing Fundamentals

## AAA Pattern (Arrange-Act-Assert)

Structure every test in three clear phases:

```typescript
test('calculates total with discount', () => {
  // Arrange - set up test data
  const cart = createCart([
    { id: '1', price: 100, quantity: 2 },
    { id: '2', price: 50, quantity: 1 }
  ]);
  const discount = 0.1; // 10%

  // Act - perform the action
  const total = calculateTotal(cart, discount);

  // Assert - verify outcome
  expect(total).toBe(225); // (200 + 50) * 0.9
});
```

## Test Isolation

Each test must be independent:

```typescript
// Use beforeEach for fresh state
beforeEach(() => {
  vi.clearAllMocks();
  testDb = createTestDatabase();
});

afterEach(async () => {
  await testDb.cleanup();
});

// Tests don't depend on order
test('test A', () => { /* ... */ });
test('test B', () => { /* ... */ }); // Works regardless of A
```

## Given-When-Then Pattern

For behavior-driven tests:

```typescript
describe('User registration', () => {
  test('given valid email, when registering, then creates account', async () => {
    // Given
    const email = 'new@example.com';
    const password = 'SecurePass123!';

    // When
    const result = await registerUser(email, password);

    // Then
    expect(result.success).toBe(true);
    expect(result.user.email).toBe(email);
  });
});
```

## Test Naming Conventions

```typescript
// Pattern: [unit]_[scenario]_[expected outcome]
test('calculateTax_negativeAmount_throwsError', () => { });
test('validateEmail_missingAtSymbol_returnsFalse', () => { });
test('formatDate_nullInput_returnsEmptyString', () => { });

// Or descriptive sentence style
test('should throw error when amount is negative', () => { });
test('returns false for email without @ symbol', () => { });
```

## Test Coverage Philosophy

- **Line Coverage**: % of code lines executed
- **Branch Coverage**: % of if/else paths taken
- **Function Coverage**: % of functions called

**Targets:**
- Business logic: 90%+
- Critical paths (auth, payments): 100%
- UI components: 70%+
- Utilities: 80%+

**Remember:** Coverage is a metric, not a goal. 100% coverage != bug-free.

## What to Test

**DO test:**
- Business logic and calculations
- Edge cases and boundaries
- Error handling paths
- State transitions

**DON'T test:**
- Framework internals
- Third-party library behavior
- Implementation details
- Trivial getters/setters
