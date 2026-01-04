#!/usr/bin/env python3
"""Restore filtered Langfuse config from SQL backup.

Restores only configuration tables, excludes runtime data and credentials.
Preserves test environment credentials and user accounts.

Based on 2025/2026 best practices for environment separation.

Usage:
    poetry run python scripts/restore_langfuse_db_filtered.py \
        --backup backend/data/langfuse_db_backups/langfuse_backup_20260103_155156.sql \
        --container skillforge-langfuse-db-test
"""

import argparse
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Import extract script function
from extract_langfuse_config_tables import extract_config_tables

CONTAINER_NAME = "skillforge-langfuse-db-test"
DB_USER = "langfuse"
DB_NAME = "langfuse"


def backup_current_database(container_name: str, db_user: str, db_name: str) -> Path:
    """Backup current test database before restore."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = Path(f"/tmp/langfuse_test_backup_{timestamp}.sql")

    print(f"📦 Backing up current test database...")
    print(f"   Container: {container_name}")
    print(f"   Database: {db_name}")

    try:
        result = subprocess.run(
            [
                "docker",
                "exec",
                container_name,
                "pg_dump",
                "-U",
                db_user,
                db_name,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        with open(backup_file, "w") as f:
            f.write(result.stdout)

        print(f"   ✅ Backup saved: {backup_file}")
        return backup_file
    except subprocess.CalledProcessError as e:
        print(f"   ⚠️  Warning: Backup failed: {e}")
        print(f"   Continuing without backup...")
        return None


def restore_filtered_backup(
    container_name: str, db_user: str, db_name: str, filtered_sql: Path
) -> None:
    """Restore filtered SQL backup to test database.
    
    Uses ON CONFLICT handling to skip CREATE TABLE errors for existing tables.
    """
    print(f"\n🔄 Restoring filtered backup...")
    print(f"   File: {filtered_sql}")

    try:
        # Read filtered SQL
        with open(filtered_sql, "r") as f:
            sql_content = f.read()
        
        # Filter out CREATE TABLE statements (tables already exist)
        # Keep only COPY blocks and data
        lines = sql_content.split("\n")
        filtered_lines = []
        skip_create = False
        
        for line in lines:
            # Skip CREATE TABLE statements (tables already exist from migrations)
            if line.strip().startswith("CREATE TABLE"):
                skip_create = True
                continue
            if skip_create and line.strip().endswith(";"):
                skip_create = False
                continue
            if not skip_create:
                filtered_lines.append(line)
        
        filtered_sql_content = "\n".join(filtered_lines)
        
        # Restore data only (COPY blocks)
        result = subprocess.run(
            ["docker", "exec", "-i", container_name, "psql", "-U", db_user, db_name],
            input=filtered_sql_content,
            capture_output=True,
            text=True,
            check=False,  # Don't fail on warnings
        )

        # Check for actual errors (not just "already exists" warnings)
        if result.returncode != 0:
            errors = [line for line in result.stderr.split("\n") 
                     if "ERROR" in line and "already exists" not in line]
            if errors:
                print(f"   ❌ Restore failed with errors:")
                for error in errors[:5]:
                    print(f"      {error}")
                raise subprocess.CalledProcessError(result.returncode, "psql", result.stderr)
        
        print(f"   ✅ Restore complete!")
        if result.stderr:
            # Filter out "already exists" warnings (expected)
            warnings = [line for line in result.stderr.split("\n") 
                       if "already exists" not in line and line.strip()]
            if warnings:
                print(f"   Warnings: {len(warnings)} non-critical warnings")
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Restore failed: {e}")
        print(f"   Error output: {e.stderr}")
        raise


def verify_restore(container_name: str, db_user: str, db_name: str) -> dict:
    """Verify restore integrity by checking table counts."""
    print(f"\n🔍 Verifying restore...")

    verify_query = """
    SELECT 
        'score_configs' as table_name, COUNT(*) as count FROM score_configs
    UNION ALL
    SELECT 'prompts', COUNT(*) FROM prompts
    UNION ALL
    SELECT 'datasets', COUNT(*) FROM datasets
    UNION ALL
    SELECT 'annotation_queues', COUNT(*) FROM annotation_queues
    UNION ALL
    SELECT 'projects', COUNT(*) FROM projects
    UNION ALL
    SELECT 'organizations', COUNT(*) FROM organizations;
    """

    try:
        result = subprocess.run(
            [
                "docker",
                "exec",
                container_name,
                "psql",
                "-U",
                db_user,
                "-d",
                db_name,
                "-c",
                verify_query,
                "-t",  # Tuples only
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        counts = {}
        for line in result.stdout.strip().split("\n"):
            if "|" in line:
                table, count = line.split("|")
                counts[table.strip()] = int(count.strip())

        print("   ✅ Restore verification:")
        for table, count in counts.items():
            print(f"      {table}: {count} rows")

        return counts
    except subprocess.CalledProcessError as e:
        print(f"   ⚠️  Verification failed: {e}")
        return {}


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Restore filtered Langfuse config from SQL backup"
    )
    parser.add_argument(
        "--backup",
        type=Path,
        required=True,
        help="Input SQL backup file",
    )
    parser.add_argument(
        "--container",
        type=str,
        default=CONTAINER_NAME,
        help=f"Docker container name (default: {CONTAINER_NAME})",
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip backing up current database before restore",
    )

    args = parser.parse_args()

    if not args.backup.exists():
        print(f"❌ Error: Backup file not found: {args.backup}")
        sys.exit(1)

    # Step 1: Backup current database
    if not args.skip_backup:
        backup_file = backup_current_database(args.container, DB_USER, DB_NAME)
        if backup_file:
            print(f"\n💾 Backup saved for rollback: {backup_file}")

    # Step 2: Extract config tables
    print(f"\n📋 Extracting config tables from backup...")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as tmp:
        filtered_sql = Path(tmp.name)
        extract_config_tables(args.backup, filtered_sql)

    # Step 3: Restore filtered backup
    restore_filtered_backup(args.container, DB_USER, DB_NAME, filtered_sql)

    # Step 4: Verify restore
    counts = verify_restore(args.container, DB_USER, DB_NAME)

    # Cleanup
    filtered_sql.unlink()

    print(f"\n✅ Restore complete!")
    print(f"\n📋 Next steps:")
    print(f"   1. Restart langfuse-web: docker compose -f docker-compose.test.yml restart langfuse-web")
    print(f"   2. Verify in UI: http://localhost:3001")
    print(f"   3. Check prompts, score_configs, datasets, annotation_queues")


if __name__ == "__main__":
    main()
