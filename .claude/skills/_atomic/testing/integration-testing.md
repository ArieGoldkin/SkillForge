---
name: integration-testing
description: Integration test patterns for APIs, databases, services
version: 1.0.0
tags: [testing, integration, api, database]
size: atomic
domain: testing
---

# Integration Testing Patterns

## What Integration Tests Cover

- API endpoint behavior
- Database operations
- Service interactions
- Component communication

**Target:** 70%+ coverage for APIs and service interactions

## API Integration Testing (FastAPI)

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_create_user(client):
    response = await client.post("/api/users", json={
        "email": "test@example.com",
        "name": "Test User"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data

@pytest.mark.asyncio
async def test_get_user_not_found(client):
    response = await client.get("/api/users/nonexistent-id")
    assert response.status_code == 404
```

## Database Integration Testing

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session

    await engine.dispose()

@pytest.mark.asyncio
async def test_user_repository(db_session):
    repo = UserRepository(db_session)

    # Create
    user = await repo.create(email="test@example.com", name="Test")
    assert user.id is not None

    # Read
    found = await repo.get_by_email("test@example.com")
    assert found.id == user.id

    # Update
    updated = await repo.update(user.id, name="Updated")
    assert updated.name == "Updated"

    # Delete
    await repo.delete(user.id)
    assert await repo.get_by_id(user.id) is None
```

## API Integration Testing (Express/Node)

```typescript
import { describe, test, expect, beforeAll, afterAll } from 'vitest'
import request from 'supertest'
import { app } from '../app'
import { db } from '../database'

beforeAll(async () => {
  await db.migrate.latest()
})

afterAll(async () => {
  await db.destroy()
})

describe('POST /api/users', () => {
  test('creates user with valid data', async () => {
    const response = await request(app)
      .post('/api/users')
      .send({ email: 'test@example.com', name: 'Test' })
      .expect(201)

    expect(response.body).toMatchObject({
      email: 'test@example.com',
      name: 'Test',
    })
    expect(response.body.id).toBeDefined()
  })

  test('returns 422 for invalid email', async () => {
    const response = await request(app)
      .post('/api/users')
      .send({ email: 'invalid', name: 'Test' })
      .expect(422)

    expect(response.body.error).toContain('email')
  })
})
```

## Test Isolation Strategies

```python
# Transaction rollback (fastest)
@pytest.fixture
async def db_session(db_engine):
    async with db_engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn)
        yield session
        await trans.rollback()  # Rollback after each test

# Fresh database (cleanest)
@pytest.fixture
async def clean_db():
    await db.drop_all()
    await db.create_all()
    yield db
    await db.drop_all()

# Truncate tables (balanced)
@pytest.fixture(autouse=True)
async def cleanup_tables(db_session):
    yield
    for table in reversed(Base.metadata.sorted_tables):
        await db_session.execute(table.delete())
    await db_session.commit()
```

## Testing External Services

```python
# Use VCR.py for HTTP services (see api-mocking-vcr)
@pytest.mark.vcr()
async def test_payment_integration():
    result = await payment_service.charge(amount=100, currency="USD")
    assert result.status == "succeeded"

# Use test containers for databases
@pytest.fixture(scope="session")
def postgres():
    with PostgresContainer("postgres:15") as pg:
        yield pg.get_connection_url()
```

## Key Principles

1. **Test real interactions** - Use actual database, real HTTP
2. **Isolate tests** - Each test starts fresh
3. **Use fixtures** - Set up common test data
4. **Clean up** - Don't leave state between tests
5. **Test boundaries** - Focus on interfaces, not internals
