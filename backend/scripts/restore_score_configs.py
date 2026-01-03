#!/usr/bin/env python3
"""Restore score configs to Langfuse via API.

Usage:
    poetry run python scripts/restore_score_configs.py
"""

import json
import os
from pathlib import Path

import httpx

# Load from backup
BACKUP_FILE = Path(__file__).parent.parent / "data" / "langfuse_evaluators_backup.json"

# Langfuse API
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")


def create_score_config(client: httpx.Client, config: dict) -> bool:
    """Create a single score config via Langfuse API."""
    # Map backup format to API format
    payload = {
        "name": config["name"],
        "dataType": config["dataType"],
        "description": config.get("description", ""),
    }

    # Add min/max for numeric types
    if config["dataType"] == "NUMERIC":
        if config.get("minValue") is not None:
            payload["minValue"] = config["minValue"]
        if config.get("maxValue") is not None:
            payload["maxValue"] = config["maxValue"]

    # Add categories for boolean/categorical types
    if config.get("categories"):
        payload["categories"] = config["categories"]

    try:
        response = client.post(
            f"{LANGFUSE_HOST}/api/public/score-configs",
            json=payload,
        )
        if response.status_code in (200, 201):
            print(f"  ✓ Created: {config['name']}")
            return True
        elif response.status_code == 409:
            print(f"  - Exists: {config['name']}")
            return True
        else:
            print(f"  ✗ Failed: {config['name']} - {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"  ✗ Error: {config['name']} - {e}")
        return False


def main():
    print("=" * 60)
    print("RESTORING SCORE CONFIGS TO LANGFUSE")
    print("=" * 60)

    if not LANGFUSE_PUBLIC_KEY or not LANGFUSE_SECRET_KEY:
        print("❌ LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY must be set")
        return

    if not BACKUP_FILE.exists():
        print(f"❌ Backup file not found: {BACKUP_FILE}")
        return

    with open(BACKUP_FILE) as f:
        backup = json.load(f)

    score_configs = backup.get("score_configs", [])
    print(f"\nFound {len(score_configs)} score configs to restore")
    print(f"Langfuse host: {LANGFUSE_HOST}\n")

    # Create HTTP client with auth
    with httpx.Client(
        auth=(LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY),
        timeout=30.0,
    ) as client:
        success = 0
        for config in score_configs:
            if create_score_config(client, config):
                success += 1

    print(f"\n{'=' * 60}")
    print(f"COMPLETE: {success}/{len(score_configs)} score configs created")
    print("=" * 60)


if __name__ == "__main__":
    main()
