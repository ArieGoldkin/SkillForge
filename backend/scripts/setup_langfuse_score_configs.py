"""Set up Langfuse Score Configs via the API.

This script creates Score Configs in Langfuse for tracking quality and performance metrics:

Legacy Quality Scores:
- user_feedback: BOOLEAN (0 or 1) - human annotation feedback
- quality_relevance: NUMERIC (0.0 to 1.0) - G-Eval LLM-as-a-Judge score (legacy)
- quality_depth: NUMERIC (0.0 to 1.0) - G-Eval LLM-as-a-Judge score (legacy)
- quality_coherence: NUMERIC (0.0 to 1.0) - G-Eval LLM-as-a-Judge score (legacy)
- quality_avg: NUMERIC (0.0 to 1.0) - Average of G-Eval scores (legacy)

G-Eval Criterion Scores:
- g_eval_relevance: NUMERIC (0.0 to 1.0) - G-Eval criterion score for relevance
- g_eval_depth: NUMERIC (0.0 to 1.0) - G-Eval criterion score for depth
- g_eval_coherence: NUMERIC (0.0 to 1.0) - G-Eval criterion score for coherence
- g_eval_actionability: NUMERIC (0.0 to 1.0) - G-Eval criterion score for actionability
- g_eval_completeness: NUMERIC (0.0 to 1.0) - G-Eval criterion score for completeness
- g_eval_overall: NUMERIC (0.0 to 1.0) - G-Eval weighted average score
- g_eval_hallucination: NUMERIC (0.0 to 1.0) - G-Eval hallucination detection score (higher = fewer hallucinations)

Performance Metrics:
- latency_seconds: NUMERIC - Execution latency in seconds
- cache_hit: BOOLEAN - Whether result was served from cache

Token & Cost Tracking (auto-captured by Langfuse CallbackHandler):
- token_count_input: NUMERIC - Input token count for LLM calls
- token_count_output: NUMERIC - Output token count for LLM calls
- token_count_total: NUMERIC - Total token count (input + output)
- cost_usd: NUMERIC - Estimated cost in USD for LLM calls

Score Configs enable:
- Validation in the Langfuse UI (type checking, range validation)
- Standardized score names across the organization
- Better analytics and dashboards

Usage:
    # Set up all score configs
    poetry run python scripts/setup_langfuse_score_configs.py

    # Dry run (show what would be created)
    poetry run python scripts/setup_langfuse_score_configs.py --dry-run

    # Force update existing configs
    poetry run python scripts/setup_langfuse_score_configs.py --force

Environment variables required:
    LANGFUSE_PUBLIC_KEY=<your-key>
    LANGFUSE_SECRET_KEY=<your-key>
    LANGFUSE_HOST=<your-host>  # Optional, defaults to http://localhost:3000

API Documentation:
    https://langfuse.com/docs/scores/custom#score-configs
"""

import argparse
import asyncio
import base64
import os
import sys
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

# Load environment variables from .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging import get_logger  # noqa: E402

logger = get_logger(__name__)

# Score Config definitions
SCORE_CONFIGS = [
    {
        "name": "user_feedback",
        "dataType": "BOOLEAN",
        "description": "Human annotation feedback from users (thumbs up/down, 0=negative 1=positive)",
    },
    {
        "name": "quality_relevance",
        "dataType": "NUMERIC",
        "description": "G-Eval LLM-as-a-Judge score for content relevance (0.0 to 1.0)",
        "minValue": 0.0,
        "maxValue": 1.0,
    },
    {
        "name": "quality_depth",
        "dataType": "NUMERIC",
        "description": "G-Eval LLM-as-a-Judge score for content depth and detail (0.0 to 1.0)",
        "minValue": 0.0,
        "maxValue": 1.0,
    },
    {
        "name": "quality_coherence",
        "dataType": "NUMERIC",
        "description": "G-Eval LLM-as-a-Judge score for content coherence and structure (0.0 to 1.0)",
        "minValue": 0.0,
        "maxValue": 1.0,
    },
    {
        "name": "quality_avg",
        "dataType": "NUMERIC",
        "description": "Average of all G-Eval quality scores (0.0 to 1.0)",
        "minValue": 0.0,
        "maxValue": 1.0,
    },
    # G-Eval criterion scores (per-criterion detailed tracking)
    {
        "name": "g_eval_relevance",
        "dataType": "NUMERIC",
        "description": "G-Eval LLM-as-a-Judge score for content relevance (0.0 to 1.0)",
        "minValue": 0.0,
        "maxValue": 1.0,
    },
    {
        "name": "g_eval_depth",
        "dataType": "NUMERIC",
        "description": "G-Eval LLM-as-a-Judge score for analytical depth (0.0 to 1.0)",
        "minValue": 0.0,
        "maxValue": 1.0,
    },
    {
        "name": "g_eval_coherence",
        "dataType": "NUMERIC",
        "description": "G-Eval LLM-as-a-Judge score for logical coherence (0.0 to 1.0)",
        "minValue": 0.0,
        "maxValue": 1.0,
    },
    {
        "name": "g_eval_actionability",
        "dataType": "NUMERIC",
        "description": "G-Eval LLM-as-a-Judge score for practical actionability (0.0 to 1.0)",
        "minValue": 0.0,
        "maxValue": 1.0,
    },
    {
        "name": "g_eval_completeness",
        "dataType": "NUMERIC",
        "description": "G-Eval LLM-as-a-Judge score for content completeness (0.0 to 1.0)",
        "minValue": 0.0,
        "maxValue": 1.0,
    },
    {
        "name": "g_eval_overall",
        "dataType": "NUMERIC",
        "description": "G-Eval overall quality score (weighted average, 0.0 to 1.0)",
        "minValue": 0.0,
        "maxValue": 1.0,
    },
    {
        "name": "g_eval_hallucination",
        "dataType": "NUMERIC",
        "description": "G-Eval hallucination detection score (0.0 to 1.0, higher = fewer hallucinations)",
        "minValue": 0.0,
        "maxValue": 1.0,
    },
    # Performance metrics
    {
        "name": "latency_seconds",
        "dataType": "NUMERIC",
        "description": "Execution latency in seconds",
        "minValue": 0.0,
    },
    {
        "name": "cache_hit",
        "dataType": "BOOLEAN",
        "description": "Whether the result was served from cache (1=hit, 0=miss)",
    },
    # Token tracking (captured by Langfuse CallbackHandler)
    {
        "name": "token_count_input",
        "dataType": "NUMERIC",
        "description": "Input token count for LLM calls",
        "minValue": 0,
    },
    {
        "name": "token_count_output",
        "dataType": "NUMERIC",
        "description": "Output token count for LLM calls",
        "minValue": 0,
    },
    {
        "name": "token_count_total",
        "dataType": "NUMERIC",
        "description": "Total token count (input + output)",
        "minValue": 0,
    },
    # Cost tracking (captured by Langfuse CallbackHandler)
    {
        "name": "cost_usd",
        "dataType": "NUMERIC",
        "description": "Estimated cost in USD for LLM calls",
        "minValue": 0.0,
    },
]


def get_auth_header() -> str:
    """Get Basic Auth header for Langfuse API.

    Returns:
        Authorization header value (Basic <base64-encoded-credentials>)

    """
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")

    if not public_key or not secret_key:
        msg = "LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY must be set"
        raise ValueError(msg)

    # Langfuse API uses Basic Auth with public_key:secret_key
    credentials = f"{public_key}:{secret_key}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"


async def get_existing_configs(client: httpx.AsyncClient, base_url: str) -> dict[str, Any]:
    """Fetch existing Score Configs from Langfuse.

    Args:
        client: httpx AsyncClient instance
        base_url: Langfuse API base URL

    Returns:
        Dictionary mapping score config names to their full config objects

    """
    try:
        response = await client.get(
            f"{base_url}/api/public/score-configs",
            headers={"Authorization": get_auth_header()},
            timeout=10.0,
        )
        response.raise_for_status()

        data = response.json()
        configs = data.get("data", [])

        logger.info(
            "existing_configs_fetched",
            count=len(configs),
            names=[c["name"] for c in configs],
        )

        # Build dict mapping name -> config
        return {config["name"]: config for config in configs}

    except httpx.HTTPStatusError as e:
        logger.error(
            "fetch_configs_failed",
            status_code=e.response.status_code,
            response=e.response.text,
            exc_info=True,
        )
        raise
    except Exception:
        logger.exception("fetch_configs_error")
        raise


async def create_score_config(
    client: httpx.AsyncClient,
    base_url: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Create a Score Config in Langfuse.

    Args:
        client: httpx AsyncClient instance
        base_url: Langfuse API base URL
        config: Score Config definition

    Returns:
        Created Score Config response

    """
    try:
        response = await client.post(
            f"{base_url}/api/public/score-configs",
            headers={
                "Authorization": get_auth_header(),
                "Content-Type": "application/json",
            },
            json=config,
            timeout=10.0,
        )
        response.raise_for_status()

        logger.info(
            "score_config_created",
            name=config["name"],
            data_type=config["dataType"],
        )

        return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(
            "create_config_failed",
            name=config["name"],
            status_code=e.response.status_code,
            response=e.response.text,
            exc_info=True,
        )
        raise
    except Exception:
        logger.exception("create_config_error", name=config["name"])
        raise


async def update_score_config(
    client: httpx.AsyncClient,
    base_url: str,
    config_id: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Update an existing Score Config in Langfuse.

    Args:
        client: httpx AsyncClient instance
        base_url: Langfuse API base URL
        config_id: ID of the Score Config to update
        config: Score Config definition

    Returns:
        Updated Score Config response

    """
    try:
        response = await client.put(
            f"{base_url}/api/public/score-configs/{config_id}",
            headers={
                "Authorization": get_auth_header(),
                "Content-Type": "application/json",
            },
            json=config,
            timeout=10.0,
        )
        response.raise_for_status()

        logger.info(
            "score_config_updated",
            name=config["name"],
            config_id=config_id,
            data_type=config["dataType"],
        )

        return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(
            "update_config_failed",
            name=config["name"],
            config_id=config_id,
            status_code=e.response.status_code,
            response=e.response.text,
            exc_info=True,
        )
        raise
    except Exception:
        logger.exception("update_config_error", name=config["name"])
        raise


async def setup_score_configs(
    *,
    dry_run: bool = False,
    force: bool = False,
) -> int:
    """Set up all Score Configs in Langfuse.

    Args:
        dry_run: If True, only show what would be created without creating
        force: If True, update existing configs instead of skipping

    Returns:
        Exit code (0 for success, 1 for failure)

    """
    # Validate environment variables
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    base_url = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

    if not public_key or not secret_key:
        logger.error(
            "credentials_missing",
            message="LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY must be set",
            public_key_set=bool(public_key),
            secret_key_set=bool(secret_key),
        )
        return 1

    logger.info(
        "setup_start",
        base_url=base_url,
        config_count=len(SCORE_CONFIGS),
        dry_run=dry_run,
        force=force,
    )

    if dry_run:
        logger.info(
            "dry_run_mode",
            message=f"Would create/update {len(SCORE_CONFIGS)} score configs",
        )
        for config in SCORE_CONFIGS:
            logger.info(
                "dry_run_config",
                name=config["name"],
                data_type=config["dataType"],
                description=config.get("description", ""),
            )
        return 0

    # Create async HTTP client
    async with httpx.AsyncClient() as client:
        try:
            # Fetch existing configs
            existing = await get_existing_configs(client, base_url)

            created_count = 0
            updated_count = 0
            skipped_count = 0
            failed_count = 0

            for config in SCORE_CONFIGS:
                config_name = config["name"]

                try:
                    if config_name in existing:
                        if force:
                            # Update existing config
                            existing_id = existing[config_name]["id"]
                            await update_score_config(client, base_url, existing_id, config)
                            updated_count += 1
                        else:
                            logger.info(
                                "config_already_exists",
                                name=config_name,
                                message="Use --force to update existing configs",
                            )
                            skipped_count += 1
                    else:
                        # Create new config
                        await create_score_config(client, base_url, config)
                        created_count += 1

                except Exception as e:
                    logger.error(
                        "config_operation_failed",
                        name=config_name,
                        error=str(e),
                        exc_info=True,
                    )
                    failed_count += 1

            # Summary
            logger.info(
                "setup_complete",
                created=created_count,
                updated=updated_count,
                skipped=skipped_count,
                failed=failed_count,
                total=len(SCORE_CONFIGS),
            )

            return 0 if failed_count == 0 else 1

        except Exception as e:
            logger.error(
                "setup_failed",
                error=str(e),
                exc_info=True,
            )
            return 1


def main() -> int:
    """Main entry point for the script.

    Returns:
        Exit code (0 for success, 1 for failure)

    """
    parser = argparse.ArgumentParser(
        description="Set up Langfuse Score Configs for quality tracking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Set up all score configs
    poetry run python scripts/setup_langfuse_score_configs.py

    # Dry run (show what would be created)
    poetry run python scripts/setup_langfuse_score_configs.py --dry-run

    # Force update existing configs
    poetry run python scripts/setup_langfuse_score_configs.py --force

Environment Variables:
    LANGFUSE_PUBLIC_KEY: Langfuse public API key (required)
    LANGFUSE_SECRET_KEY: Langfuse secret API key (required)
    LANGFUSE_HOST: Langfuse host URL (optional, defaults to http://localhost:3000)

Score Configs:
    Legacy Quality Scores:
    - user_feedback: BOOLEAN (0 or 1) - human annotation feedback
    - quality_relevance: NUMERIC (0.0 to 1.0) - G-Eval score for relevance (legacy)
    - quality_depth: NUMERIC (0.0 to 1.0) - G-Eval score for depth (legacy)
    - quality_coherence: NUMERIC (0.0 to 1.0) - G-Eval score for coherence (legacy)
    - quality_avg: NUMERIC (0.0 to 1.0) - average of all G-Eval scores (legacy)

    G-Eval Criterion Scores (per-criterion detailed tracking):
    - g_eval_relevance: NUMERIC (0.0 to 1.0) - content relevance
    - g_eval_depth: NUMERIC (0.0 to 1.0) - analytical depth
    - g_eval_coherence: NUMERIC (0.0 to 1.0) - logical coherence
    - g_eval_actionability: NUMERIC (0.0 to 1.0) - practical actionability
    - g_eval_completeness: NUMERIC (0.0 to 1.0) - content completeness
    - g_eval_overall: NUMERIC (0.0 to 1.0) - weighted average
    - g_eval_hallucination: NUMERIC (0.0 to 1.0) - hallucination detection (higher = fewer hallucinations)

    Performance Metrics:
    - latency_seconds: NUMERIC - execution latency in seconds
    - cache_hit: BOOLEAN - whether result was served from cache

    Token & Cost Tracking (auto-captured by Langfuse CallbackHandler):
    - token_count_input: NUMERIC - input token count for LLM calls
    - token_count_output: NUMERIC - output token count for LLM calls
    - token_count_total: NUMERIC - total token count (input + output)
    - cost_usd: NUMERIC - estimated cost in USD for LLM calls
        """,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without creating",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Update existing configs instead of skipping",
    )

    args = parser.parse_args()

    # Run async setup
    return asyncio.run(
        setup_score_configs(
            dry_run=args.dry_run,
            force=args.force,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
