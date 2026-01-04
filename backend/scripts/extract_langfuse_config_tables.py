#!/usr/bin/env python3
"""Extract only config tables from Langfuse SQL backup.

This script filters a PostgreSQL pg_dump backup to include only configuration tables,
excluding runtime data and credentials. Based on 2025/2026 best practices for
environment separation.

Usage:
    poetry run python scripts/extract_langfuse_config_tables.py \
        --input backend/data/langfuse_db_backups/langfuse_backup_20260103_155156.sql \
        --output /tmp/langfuse_config_filtered.sql
"""

import argparse
import re
import sys
from pathlib import Path

# Config tables to include (COPY blocks)
CONFIG_TABLES = {
    "score_configs",
    "prompts",
    "eval_templates",
    "datasets",
    "dataset_items",
    "annotation_queues",
    "annotation_queue_assignments",
    "projects",
    "organizations",
    "llm_api_keys",
    "default_llm_models",
    "llm_schemas",
    "llm_tools",
    "prompt_dependencies",
    "prompt_protected_labels",
    "sso_configs",
    "models",
    "prices",
    "pricing_tiers",
    "dashboards",
    "dashboard_widgets",
    "actions",
    "automations",
    "job_configurations",
}

# Data tables to exclude (COPY blocks)
DATA_TABLES = {
    "traces",
    "observations",
    "scores",
    "dataset_run_items",
    "dataset_runs",
    "trace_sessions",
    "sessions",
    "audit_logs",
    "observation_media",
    "trace_media",
    "dataset_item_events",
    "automation_executions",
    "job_executions",
    "batch_actions",
    "batch_exports",
    "comments",
    "comment_reactions",
}

# Credential tables to exclude (will use test credentials)
CREDENTIAL_TABLES = {
    "users",
    "api_keys",
    "organization_memberships",
    "project_memberships",
    "Account",
    "Session",
    "membership_invitations",
    "verification_tokens",
}


def extract_config_tables(input_file: Path, output_file: Path) -> None:
    """Extract only config tables from PostgreSQL COPY format backup.

    Handles PostgreSQL COPY format:
    COPY table_name (...) FROM stdin;
    ... data ...
    \.
    """
    print(f"Extracting config tables from: {input_file}")
    print(f"Output file: {output_file}")

    # Read entire file (4.2 MB is manageable)
    with open(input_file, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Extract header (SET statements, CREATE TYPE, etc.)
    header_pattern = r"^--.*?^SET\s+.*?(?=^--|^CREATE|^COPY|$)"
    header_match = re.search(
        r"^--.*?^SET\s+.*?(?=^CREATE|^COPY|$)", content, re.MULTILINE | re.DOTALL
    )
    if header_match:
        header = content[: header_match.end()]
    else:
        # Fallback: get first 200 lines
        header = "\n".join(content.split("\n")[:200])

    # Extract all CREATE TABLE statements (needed for structure)
    create_table_pattern = r"^CREATE TABLE[^;]+;"
    create_tables = re.findall(create_table_pattern, content, re.MULTILINE | re.DOTALL)

    # Extract COPY blocks for config tables only
    copy_pattern = r"(COPY\s+(?:public\.)?[\"']?(\w+)[\"']?\s+\([^)]+\)\s+FROM\s+stdin;.*?\\.)"
    copy_blocks = re.findall(copy_pattern, content, re.DOTALL | re.IGNORECASE)

    # Filter COPY blocks
    config_copy_blocks = []
    excluded_tables = set()
    for copy_block, table_name in copy_blocks:
        if table_name in CONFIG_TABLES:
            config_copy_blocks.append(copy_block)
            print(f"  ✓ Including: {table_name}")
        elif table_name in DATA_TABLES:
            excluded_tables.add(table_name)
        elif table_name in CREDENTIAL_TABLES:
            excluded_tables.add(table_name)
        else:
            # Unknown table - exclude by default for safety
            excluded_tables.add(table_name)

    # Write filtered backup
    with open(output_file, "w", encoding="utf-8") as f:
        # Write header
        f.write(header)
        f.write("\n\n")

        # Write CREATE TABLE statements (all tables - needed for structure)
        for create_table in create_tables:
            f.write(create_table)
            f.write("\n\n")

        # Write COPY blocks for config tables only
        for copy_block in config_copy_blocks:
            f.write(copy_block)
            f.write("\n\n")

    print(f"\n✅ Filtered backup created: {output_file}")
    print(f"   Config tables included: {len(config_copy_blocks)}")
    print(f"   Tables excluded: {len(excluded_tables)}")
    if excluded_tables:
        print(f"   Excluded: {', '.join(sorted(excluded_tables)[:10])}...")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract config tables from Langfuse SQL backup"
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Input SQL backup file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output filtered SQL file",
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"❌ Error: Input file not found: {args.input}")
        sys.exit(1)

    extract_config_tables(args.input, args.output)
    print("\n✅ Extraction complete!")


if __name__ == "__main__":
    main()
