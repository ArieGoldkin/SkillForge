"""Setup and verify Langfuse Annotation Queue.

This script checks if the SkillForge Review Queue exists in Langfuse and prints
the queue ID for configuration.

Langfuse Annotation Queues enable human review workflows:
- Queue items for review (artifacts, traces)
- Track review status (pending, reviewed)
- Submit annotations and scores

Usage:
    poetry run python scripts/setup_langfuse_annotation_queue.py

Environment variables required:
    LANGFUSE_ENABLED=true
    LANGFUSE_PUBLIC_KEY=<your-key>
    LANGFUSE_SECRET_KEY=<your-key>
    LANGFUSE_HOST=<your-host>  # Optional, defaults to http://localhost:3000

Output:
    - Prints queue ID if found
    - Instructions to create queue via UI if not found
    - Updates .env with LANGFUSE_ANNOTATION_QUEUE_ID

Notes:
    - As of Langfuse v3, annotation queues are managed via UI
    - No public API for queue creation (only GET and POST items)
    - Queue must be created manually at http://localhost:3000/settings

"""

import os
import sys
from pathlib import Path

import httpx

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging import get_logger

logger = get_logger(__name__)

QUEUE_NAME = "SkillForge Review Queue"


def check_langfuse_config() -> tuple[str, str, str]:
    """Check if Langfuse is configured and return credentials.

    Returns:
        Tuple of (host, public_key, secret_key)

    Raises:
        SystemExit: If Langfuse is not properly configured

    """
    langfuse_enabled = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
    if not langfuse_enabled:
        logger.error(
            "langfuse_disabled",
            message=(
                "LANGFUSE_ENABLED is not set to 'true'. "
                "Set LANGFUSE_ENABLED=true in your .env file."
            ),
        )
        sys.exit(1)

    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

    if not public_key or not secret_key:
        logger.error(
            "langfuse_credentials_missing",
            message="LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY not set",
            public_key_set=bool(public_key),
            secret_key_set=bool(secret_key),
        )
        sys.exit(1)

    # Type narrowing: We've validated these are not None above
    assert public_key is not None
    assert secret_key is not None

    return host, public_key, secret_key


async def list_annotation_queues(host: str, public_key: str, secret_key: str) -> list[dict]:
    """List all annotation queues via Langfuse Public API.

    Args:
        host: Langfuse host URL
        public_key: Langfuse public key
        secret_key: Langfuse secret key

    Returns:
        List of annotation queue objects

    Raises:
        httpx.HTTPError: If API request fails

    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{host}/api/public/annotation-queues",
            auth=(public_key, secret_key),
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()

        # API returns {data: [...], meta: {...}}
        return data.get("data", [])


def update_env_file(queue_id: str) -> None:
    """Update .env file with LANGFUSE_ANNOTATION_QUEUE_ID.

    Args:
        queue_id: Queue ID to add to .env

    """
    env_path = Path(__file__).parent.parent / ".env"

    if not env_path.exists():
        logger.warning(
            "env_file_not_found",
            message=".env file not found, creating from .env.example",
            path=str(env_path),
        )
        example_path = Path(__file__).parent.parent / ".env.example"
        if example_path.exists():
            env_path.write_text(example_path.read_text())
        else:
            env_path.touch()

    env_content = env_path.read_text()

    # Check if LANGFUSE_ANNOTATION_QUEUE_ID already exists
    if "LANGFUSE_ANNOTATION_QUEUE_ID=" in env_content:
        # Replace existing value
        lines = env_content.split("\n")
        new_lines = []
        for line in lines:
            if line.startswith("LANGFUSE_ANNOTATION_QUEUE_ID="):
                new_lines.append(f"LANGFUSE_ANNOTATION_QUEUE_ID={queue_id}")
                logger.info(
                    "env_var_updated",
                    message="Updated existing LANGFUSE_ANNOTATION_QUEUE_ID in .env",
                    queue_id=queue_id,
                )
            else:
                new_lines.append(line)
        env_path.write_text("\n".join(new_lines))
    else:
        # Add new value
        if not env_content.endswith("\n"):
            env_content += "\n"
        env_content += f"\n# Langfuse Annotation Queue (auto-configured)\nLANGFUSE_ANNOTATION_QUEUE_ID={queue_id}\n"
        env_path.write_text(env_content)
        logger.info(
            "env_var_added",
            message="Added LANGFUSE_ANNOTATION_QUEUE_ID to .env",
            queue_id=queue_id,
        )


async def main() -> None:
    """Main script entry point."""
    print("=" * 70)
    print("Langfuse Annotation Queue Setup")
    print("=" * 70)
    print()

    # Check configuration
    print("1. Checking Langfuse configuration...")
    host, public_key, secret_key = check_langfuse_config()
    print(f"   ✓ Host: {host}")
    print(f"   ✓ Public key: {public_key[:10]}...")
    print(f"   ✓ Secret key: {secret_key[:10]}...")
    print()

    # List annotation queues
    print("2. Fetching annotation queues...")
    try:
        queues = await list_annotation_queues(host, public_key, secret_key)
        print(f"   ✓ Found {len(queues)} queue(s)")
        print()
    except httpx.HTTPError as e:
        logger.error(
            "api_request_failed",
            error=str(e),
            message="Failed to fetch annotation queues from Langfuse API",
            exc_info=True,
        )
        print(f"   ✗ Error: {e}")
        print()
        print("Troubleshooting:")
        print("  - Ensure Langfuse is running: docker-compose ps langfuse-web")
        print(f"  - Verify Langfuse UI is accessible: {host}")
        print("  - Check API keys are correct in .env")
        sys.exit(1)

    # Find SkillForge Review Queue
    print(f"3. Looking for '{QUEUE_NAME}'...")
    skillforge_queue = None
    for queue in queues:
        if queue.get("name") == QUEUE_NAME:
            skillforge_queue = queue
            break

    if skillforge_queue:
        queue_id = skillforge_queue["id"]
        print(f"   ✓ Found queue ID: {queue_id}")
        print()

        # Update .env file
        print("4. Updating .env file...")
        update_env_file(queue_id)
        print(f"   ✓ Added LANGFUSE_ANNOTATION_QUEUE_ID={queue_id}")
        print()

        print("=" * 70)
        print("✅ Setup Complete!")
        print("=" * 70)
        print()
        print("Queue Details:")
        print(f"  Name: {skillforge_queue.get('name')}")
        print(f"  ID: {queue_id}")
        print(f"  Description: {skillforge_queue.get('description', 'N/A')}")
        print()
        print("Next Steps:")
        print("  1. Restart the backend to load the new env var")
        print("  2. Submit feedback to queue an artifact for review")
        print(f"  3. View queue in Langfuse UI: {host}/annotation-queues/{queue_id}")

    else:
        print(f"   ✗ Queue '{QUEUE_NAME}' not found")
        print()
        print("=" * 70)
        print("📝 Manual Setup Required")
        print("=" * 70)
        print()
        print("The annotation queue must be created via Langfuse UI:")
        print()
        print("Steps:")
        print(f"  1. Open Langfuse UI: {host}")
        print("  2. Navigate to Settings → Annotation Queues")
        print("  3. Click 'Create Queue'")
        print(f"  4. Name: {QUEUE_NAME}")
        print("  5. Description: Queue for reviewing SkillForge artifacts")
        print("  6. Save the queue")
        print("  7. Run this script again to get the queue ID")
        print()
        print("Note: Langfuse v3 does not provide a public API for queue creation.")
        print("      Queues must be created manually via the UI.")
        print()

        if queues:
            print("Existing Queues:")
            for queue in queues:
                print(f"  - {queue.get('name')} (ID: {queue.get('id')})")
            print()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
