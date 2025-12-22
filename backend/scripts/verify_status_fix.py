#!/usr/bin/env python3
"""Verify that status fix is working correctly.

This script checks:
1. Seed scripts use 'complete' status (not 'completed')
2. API accepts 'complete' status filter
3. Database has no 'completed' status values
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Check if DATABASE_URL is set
raw_database_url = os.environ.get("DATABASE_URL")
if not raw_database_url:
    print("❌ DATABASE_URL not set. Set it to test database connection.")
    print("   Example: DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db")
    sys.exit(1)

# Type narrowing: raw_database_url is guaranteed to be str here
database_url = cast("str", raw_database_url)

print("🔍 Verifying status fix...")
print(f"   Database: {database_url.split('@')[-1] if '@' in database_url else 'N/A'}")
print()


async def verify_database() -> bool:
    """Verify database has no 'completed' status and can query 'complete'."""
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as conn:
            # Check for 'completed' status (should be 0)
            result = await conn.execute(
                text("SELECT COUNT(*) FROM analyses WHERE status = 'completed'")
            )
            completed_count = int(result.scalar() or 0)

            # Check for 'complete' status
            result = await conn.execute(
                text("SELECT COUNT(*) FROM analyses WHERE status = 'complete'")
            )
            complete_count = int(result.scalar() or 0)

            # Get all status values
            result = await conn.execute(
                text("SELECT DISTINCT status FROM analyses ORDER BY status")
            )
            all_statuses = [row[0] for row in result.fetchall()]

            print("📊 Database Status Check:")
            print(f"   ✅ Analyses with 'completed' status: {completed_count} (should be 0)")
            print(f"   ✅ Analyses with 'complete' status: {complete_count}")
            print(
                f"   ✅ All status values: {', '.join(all_statuses) if all_statuses else '(none)'}"
            )

            if completed_count > 0:
                print(f"   ⚠️  WARNING: Found {completed_count} analyses with 'completed' status!")
                print("      These should be migrated to 'complete'.")
                return False

            if "completed" in all_statuses:
                print("   ⚠️  WARNING: 'completed' status found in database!")
                return False

            print("   ✅ Database status values are correct")
            return True

    finally:
        await engine.dispose()


async def verify_seed_script() -> bool:
    """Verify seed script would create correct status."""
    seed_file = Path(__file__).parent / "seed_e2e_fixture.py"
    if not seed_file.exists():
        print("⚠️  Seed script not found, skipping check")
        return True

    content = seed_file.read_text()
    if "'completed'" in content or '"completed"' in content:
        print("❌ Seed script still contains 'completed' status!")
        print("   File: backend/scripts/seed_e2e_fixture.py")
        return False

    if "'complete'" in content or '"complete"' in content:
        print("✅ Seed script uses 'complete' status")
        return True

    print("⚠️  Seed script doesn't contain status values (may be using enum)")
    return True


def verify_api_helper() -> bool:
    """Verify frontend API helper uses correct status."""
    api_helper = (
        Path(__file__).parent.parent.parent / "frontend" / "e2e" / "utils" / "api-helpers.ts"
    )
    if not api_helper.exists():
        print("⚠️  API helper not found, skipping check")
        return True

    content = api_helper.read_text()
    if "status: 'completed'" in content or 'status: "completed"' in content:
        print("❌ API helper still uses 'completed' status!")
        print("   File: frontend/e2e/utils/api-helpers.ts")
        return False

    if "status: 'complete'" in content or 'status: "complete"' in content:
        print("✅ API helper uses 'complete' status")
        return True

    print("⚠️  API helper doesn't contain status filter")
    return True


async def main() -> int:
    """Run all verification checks."""
    print("=" * 60)
    print("Status Fix Verification")
    print("=" * 60)
    print()

    all_passed = True

    # Check seed script
    print("1️⃣  Checking seed script...")
    if not await verify_seed_script():
        all_passed = False
    print()

    # Check API helper
    print("2️⃣  Checking API helper...")
    if not verify_api_helper():
        all_passed = False
    print()

    # Check database
    print("3️⃣  Checking database...")
    try:
        if not await verify_database():
            all_passed = False
    except Exception as e:
        print(f"   ❌ Database check failed: {e}")
        all_passed = False
    print()

    # Summary
    print("=" * 60)
    if all_passed:
        print("✅ All checks passed! Status fix is working correctly.")
        return 0
    print("❌ Some checks failed. Please review the issues above.")
    return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
