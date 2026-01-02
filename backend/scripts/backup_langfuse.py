#!/usr/bin/env python3
"""Backup and restore Langfuse configurations.

This script exports all Langfuse configurations to JSON files that can be
version controlled and restored after container rebuilds.

Usage:
    poetry run python scripts/backup_langfuse.py backup
    poetry run python scripts/backup_langfuse.py restore
    poetry run python scripts/backup_langfuse.py verify
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langfuse import Langfuse

BACKUP_DIR = Path(__file__).parent.parent / "data" / "langfuse_backups"
PROMPTS_BACKUP = BACKUP_DIR / "prompts_backup.json"
DATASETS_BACKUP = BACKUP_DIR / "datasets_backup.json"
SCORE_CONFIGS_BACKUP = BACKUP_DIR / "score_configs_backup.json"
LLM_CONNECTIONS_BACKUP = BACKUP_DIR / "llm_connections_backup.json"
BACKUP_METADATA = BACKUP_DIR / "backup_metadata.json"


def backup_prompts(client: Langfuse) -> dict[str, Any]:
    """Export all Langfuse prompts to JSON."""
    print("Exporting prompts...")

    # Use the Langfuse API to list all prompts
    # The client.get_prompts() method doesn't exist - we need to use the API directly
    try:
        # Get all prompts via API
        prompts_response = client.api.prompts.list()
        prompts = prompts_response.data if hasattr(prompts_response, "data") else []
    except Exception as e:
        print(f"  ⚠ Failed to list prompts: {e}")
        print("  Note: Prompts may need to be manually documented if API access is limited")
        return {"prompts": [], "count": 0, "error": str(e)}

    exported = []
    for prompt in prompts:
        try:
            # Get full prompt details
            prompt_data = {
                "name": prompt.name if hasattr(prompt, "name") else "unknown",
                "version": prompt.version if hasattr(prompt, "version") else 1,
                "prompt": prompt.prompt if hasattr(prompt, "prompt") else "",
                "config": prompt.config if hasattr(prompt, "config") else {},
                "labels": prompt.labels if hasattr(prompt, "labels") else [],
                "tags": prompt.tags if hasattr(prompt, "tags") else [],
            }
            exported.append(prompt_data)
            print(f"  - {prompt_data['name']} (v{prompt_data['version']})")
        except Exception as e:
            print(f"  ⚠ Failed to export prompt: {e}")

    return {"prompts": exported, "count": len(exported)}


def backup_datasets(client: Langfuse) -> dict[str, Any]:
    """Export all Langfuse datasets to JSON."""
    print("\nExporting datasets...")

    try:
        # Try to get datasets via API
        # Note: This depends on Langfuse SDK version/API availability
        datasets_data = {
            "datasets": [],
            "count": 0,
            "note": "Dataset export via API not yet implemented - configure manually",
        }
        print("  ⚠ Dataset export via API not available - manual documentation required")
        return datasets_data
    except Exception as e:
        print(f"  ⚠ Dataset export failed: {e}")
        return {
            "datasets": [],
            "count": 0,
            "error": str(e),
            "note": "Configure datasets manually in Langfuse UI",
        }


def backup_score_configs() -> dict[str, Any]:
    """Document score configurations (manual documentation).

    Note: Langfuse SDK doesn't provide direct API for score configs.
    This function documents the expected configurations.
    """
    print("\nDocumenting score configurations...")

    # Document expected score configs based on SkillForge requirements
    score_configs = {
        "configs": [
            {
                "name": "quality",
                "type": "NUMERIC",
                "min_value": 0,
                "max_value": 10,
                "description": "G-Eval quality score (0-10) for analysis depth and accuracy",
                "note": "Configure in Langfuse UI: Settings → Scores → Add Score Config",
            },
            {
                "name": "depth_score",
                "type": "NUMERIC",
                "min_value": 0,
                "max_value": 10,
                "description": "Analysis depth score (0-10)",
                "note": "Configure in Langfuse UI: Settings → Scores → Add Score Config",
            },
            {
                "name": "accuracy_score",
                "type": "NUMERIC",
                "min_value": 0,
                "max_value": 10,
                "description": "Technical accuracy score (0-10)",
                "note": "Configure in Langfuse UI: Settings → Scores → Add Score Config",
            },
            {
                "name": "relevance_score",
                "type": "NUMERIC",
                "min_value": 0,
                "max_value": 10,
                "description": "Relevance to user goals score (0-10)",
                "note": "Configure in Langfuse UI: Settings → Scores → Add Score Config",
            },
            {
                "name": "coherence_score",
                "type": "NUMERIC",
                "min_value": 0,
                "max_value": 10,
                "description": "Output coherence score (0-10)",
                "note": "Configure in Langfuse UI: Settings → Scores → Add Score Config",
            },
        ],
        "count": 5,
        "note": "These must be configured manually in Langfuse UI (Settings → Scores)",
    }

    for config in score_configs["configs"]:
        print(
            f"  - {config['name']} ({config['type']}, {config['min_value']}-{config['max_value']})"
        )

    return score_configs


def backup_llm_connections() -> dict[str, Any]:
    """Document LLM connections (manual documentation).

    Note: LLM connection credentials shouldn't be in git - this documents the structure.
    """
    print("\nDocumenting LLM connections...")

    # Document expected LLM connections
    llm_connections = {
        "connections": [
            {
                "name": "OpenAI GPT-4o-mini",
                "provider": "openai",
                "model": "gpt-4o-mini",
                "use_case": "Main agent LLM for cost efficiency",
                "note": "Configure in Langfuse UI: Settings → LLM API Keys → OpenAI",
            },
            {
                "name": "Anthropic Claude 3.5 Sonnet",
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
                "use_case": "High-quality analysis and reasoning",
                "note": "Configure in Langfuse UI: Settings → LLM API Keys → Anthropic",
            },
            {
                "name": "Google Gemini 2.0 Flash",
                "provider": "google",
                "model": "gemini-2.0-flash-exp",
                "use_case": "G-Eval quality scoring",
                "note": "Configure in Langfuse UI: Settings → LLM API Keys → Google",
            },
        ],
        "count": 3,
        "warning": "DO NOT commit API keys - configure manually in Langfuse UI",
        "note": "This documents the required connections, not the actual credentials",
    }

    for conn in llm_connections["connections"]:
        print(f"  - {conn['name']} ({conn['provider']})")

    return llm_connections


def create_backup(client: Langfuse) -> None:
    """Create full backup of all Langfuse configurations."""
    print("=" * 60)
    print("LANGFUSE CONFIGURATION BACKUP")
    print("=" * 60)

    # Ensure backup directory exists
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # Backup each component
    prompts_data = backup_prompts(client)
    datasets_data = backup_datasets(client)
    score_configs_data = backup_score_configs()
    llm_connections_data = backup_llm_connections()

    # Save backups
    print("\nSaving backups...")

    with open(PROMPTS_BACKUP, "w") as f:
        json.dump(prompts_data, f, indent=2)
    print(f"  ✓ Prompts: {PROMPTS_BACKUP}")

    with open(DATASETS_BACKUP, "w") as f:
        json.dump(datasets_data, f, indent=2)
    print(f"  ✓ Datasets: {DATASETS_BACKUP}")

    with open(SCORE_CONFIGS_BACKUP, "w") as f:
        json.dump(score_configs_data, f, indent=2)
    print(f"  ✓ Score Configs: {SCORE_CONFIGS_BACKUP}")

    with open(LLM_CONNECTIONS_BACKUP, "w") as f:
        json.dump(llm_connections_data, f, indent=2)
    print(f"  ✓ LLM Connections: {LLM_CONNECTIONS_BACKUP}")

    # Create metadata
    metadata = {
        "backup_timestamp": datetime.now(UTC).isoformat(),
        "langfuse_host": getattr(client, "_base_url", "http://localhost:3000"),
        "prompts_count": prompts_data["count"],
        "datasets_count": datasets_data["count"],
        "score_configs_count": score_configs_data["count"],
        "llm_connections_count": llm_connections_data["count"],
    }

    with open(BACKUP_METADATA, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"  ✓ Metadata: {BACKUP_METADATA}")

    print("\n" + "=" * 60)
    print("BACKUP COMPLETE")
    print("=" * 60)
    print(f"Prompts: {prompts_data['count']}")
    print(f"Datasets: {datasets_data['count']} (manual)")
    print(f"Score Configs: {score_configs_data['count']} (manual)")
    print(f"LLM Connections: {llm_connections_data['count']} (manual)")
    print("\nBackup location: data/langfuse_backups/")
    print("\nIMPORTANT: Manual configurations required:")
    print("  - Score configs: Langfuse UI → Settings → Scores")
    print("  - LLM connections: Langfuse UI → Settings → LLM API Keys")
    print("  - Datasets: Create manually if needed")


def restore_prompts(client: Langfuse) -> None:
    """Restore prompts from backup."""
    print("Restoring prompts...")

    if not PROMPTS_BACKUP.exists():
        print("  ⚠ No prompts backup found")
        return

    with open(PROMPTS_BACKUP) as f:
        data = json.load(f)

    prompts = data.get("prompts", [])
    print(f"  Found {len(prompts)} prompts to restore")

    for prompt_data in prompts:
        try:
            # Create or update prompt
            client.create_prompt(
                name=prompt_data["name"],
                prompt=prompt_data["prompt"],
                config=prompt_data.get("config"),
                labels=prompt_data.get("labels", []),
                tags=prompt_data.get("tags", []),
            )
            print(f"  ✓ {prompt_data['name']}")
        except Exception as e:
            print(f"  ⚠ Failed to restore {prompt_data['name']}: {e}")


def restore_backup(client: Langfuse) -> None:
    """Restore all Langfuse configurations from backup."""
    print("=" * 60)
    print("LANGFUSE CONFIGURATION RESTORE")
    print("=" * 60)

    if not BACKUP_DIR.exists():
        print("\n❌ No backup directory found!")
        print("Run 'poetry run python scripts/backup_langfuse.py backup' first")
        sys.exit(1)

    # Restore each component
    restore_prompts(client)

    print("\n" + "=" * 60)
    print("RESTORE COMPLETE")
    print("=" * 60)
    print("\nREMAINING MANUAL STEPS:")
    print("1. Score Configs: Open Langfuse UI → Settings → Scores")
    print(f"   Reference: {SCORE_CONFIGS_BACKUP}")
    print("2. LLM Connections: Open Langfuse UI → Settings → LLM API Keys")
    print(f"   Reference: {LLM_CONNECTIONS_BACKUP}")
    print("3. Datasets: Create manually if needed")
    print(f"   Reference: {DATASETS_BACKUP}")


def verify_backup() -> None:
    """Verify backup integrity and completeness."""
    print("=" * 60)
    print("LANGFUSE BACKUP VERIFICATION")
    print("=" * 60)

    if not BACKUP_DIR.exists():
        print("\n❌ No backup directory found!")
        sys.exit(1)

    # Check all backup files
    files_to_check = [
        (PROMPTS_BACKUP, "Prompts"),
        (DATASETS_BACKUP, "Datasets"),
        (SCORE_CONFIGS_BACKUP, "Score Configs"),
        (LLM_CONNECTIONS_BACKUP, "LLM Connections"),
        (BACKUP_METADATA, "Metadata"),
    ]

    all_exist = True
    for file_path, name in files_to_check:
        if file_path.exists():
            # Verify JSON is valid
            try:
                with open(file_path) as f:
                    data = json.load(f)
                count = data.get("count", "N/A")
                print(f"✓ {name}: {file_path.name} (count: {count})")
            except json.JSONDecodeError:
                print(f"⚠ {name}: {file_path.name} (INVALID JSON)")
                all_exist = False
        else:
            print(f"❌ {name}: {file_path.name} (MISSING)")
            all_exist = False

    # Check metadata
    if BACKUP_METADATA.exists():
        with open(BACKUP_METADATA) as f:
            metadata = json.load(f)
        print("\n" + "=" * 60)
        print("BACKUP METADATA")
        print("=" * 60)
        print(f"Timestamp: {metadata.get('backup_timestamp', 'N/A')}")
        print(f"Langfuse Host: {metadata.get('langfuse_host', 'N/A')}")
        print(f"Prompts: {metadata.get('prompts_count', 0)}")
        print(f"Datasets: {metadata.get('datasets_count', 0)}")
        print(f"Score Configs: {metadata.get('score_configs_count', 0)}")
        print(f"LLM Connections: {metadata.get('llm_connections_count', 0)}")

    print("\n" + "=" * 60)
    if all_exist:
        print("VERIFICATION PASSED")
    else:
        print("VERIFICATION FAILED - Missing or invalid files")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Backup and restore Langfuse configurations")
    parser.add_argument("action", choices=["backup", "restore", "verify"], help="Action to perform")

    args = parser.parse_args()

    if args.action == "verify":
        verify_backup()
        return

    # Initialize Langfuse client
    try:
        client = Langfuse()
        # Try to get base URL (private attribute)
        base_url = getattr(client, "_base_url", "http://localhost:3000")
        print(f"Connected to Langfuse at {base_url}")

        # Verify connection with auth check
        client.auth_check()
        print("Authentication successful")
    except Exception as e:
        print(f"❌ Failed to connect to Langfuse: {e}")
        print("\nEnsure:")
        print("  - Langfuse container is running: docker compose ps")
        print("  - Environment variables are set (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY)")
        sys.exit(1)

    if args.action == "backup":
        create_backup(client)
    elif args.action == "restore":
        restore_backup(client)


if __name__ == "__main__":
    main()
