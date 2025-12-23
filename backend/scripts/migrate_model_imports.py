#!/usr/bin/env python3
"""Migrate all imports from app.models to app.db.models."""

import re
import sys
from pathlib import Path


def migrate_imports(file_path: Path) -> bool:
    """Update imports in a single file. Returns True if changes were made."""
    try:
        content = file_path.read_text(encoding="utf-8")
        original_content = content

        # Pattern 1: from app.db.models import ...
        content = re.sub(r"from app\.models import", "from app.db.models import", content)

        # Pattern 2: from app.db.models.module import ...
        content = re.sub(r"from app\.models\.", "from app.db.models.", content)

        # Pattern 3: import app.db.models (rare but possible)
        content = re.sub(r"import app\.models", "import app.db.models", content)

        if content != original_content:
            file_path.write_text(content, encoding="utf-8")
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}", file=sys.stderr)
        return False


def main():
    """Find and update all Python files with model imports."""
    backend_dir = Path(__file__).parent.parent

    # Find all Python files
    python_files = []
    for pattern in ["**/*.py"]:
        python_files.extend(backend_dir.glob(pattern))

    # Exclude virtual env, caches, and node_modules
    exclude_patterns = [".venv", "node_modules", "__pycache__", ".pytest_cache", ".git"]
    python_files = [
        f for f in python_files if not any(pattern in str(f) for pattern in exclude_patterns)
    ]

    # Process files
    updated_count = 0
    total_checked = 0

    for file_path in python_files:
        total_checked += 1
        if migrate_imports(file_path):
            updated_count += 1
            print(f"Updated: {file_path.relative_to(backend_dir)}")

    print(f"\n✓ Migration complete!")
    print(f"  Files checked: {total_checked}")
    print(f"  Files updated: {updated_count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
