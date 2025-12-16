#!/usr/bin/env python3
"""CLI script to generate cutting-edge evaluation examples.

This script generates examples for 4 cutting-edge topics (Dec 2025):
1. A2A Protocol (Google) - Agent-to-Agent communication
2. MCP Nov 2025 - Model Context Protocol updates
3. Context Engineering - Advanced prompt engineering
4. LangGraph Multi-Agent - Multi-agent orchestration

Usage:
    # Generate all topics (default 4 examples each = 16 total)
    python scripts/generate_cutting_edge.py --output datasets/cutting_edge.json

    # Generate specific topic with custom count
    python scripts/generate_cutting_edge.py --topic mcp_nov_2025 --count 6 --output mcp.json

    # With validation
    python scripts/generate_cutting_edge.py --output cutting_edge.json --validate

    # With seed for reproducibility
    python scripts/generate_cutting_edge.py --seed 42 --output cutting_edge.json
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.evaluation.ingestion.cutting_edge_generator import (
    ALL_TOPICS,
    CuttingEdgeConfig,
    CuttingEdgeGenerator,
    Topic,
)
from app.evaluation.schemas.validation import validate_dataset


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate cutting-edge evaluation examples (Dec 2025)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate all topics (16 examples)
  python scripts/generate_cutting_edge.py --output cutting_edge.json

  # Generate MCP Nov 2025 only (6 examples)
  python scripts/generate_cutting_edge.py --topic mcp_nov_2025 --count 6 --output mcp.json

  # With seed for reproducibility
  python scripts/generate_cutting_edge.py --seed 42 --output cutting_edge.json

Topics:
  - a2a_protocol: Google A2A Agent Communication Protocol
  - mcp_nov_2025: Model Context Protocol November 2025 updates
  - context_engineering: Advanced prompt engineering techniques
  - langgraph_multiagent: LangGraph multi-agent orchestration
        """,
    )

    parser.add_argument(
        "--topic",
        type=str,
        choices=[t.value for t in ALL_TOPICS],
        help="Specific topic to generate (default: all topics)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=4,
        help="Number of examples per topic (default: 4)",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output JSON file path",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate generated dataset against v2.0 schema",
    )

    args = parser.parse_args()

    # Build config
    topic_enum = Topic(args.topic) if args.topic else None
    config = CuttingEdgeConfig(
        topic=topic_enum,
        count_per_topic=args.count,
        seed=args.seed,
    )

    # Generate examples
    print("Generating cutting-edge examples...")
    if config.topic:
        print(f"  Topic: {config.topic.value}")
    else:
        print(f"  Topics: all ({len(ALL_TOPICS)})")
    print(f"  Count per topic: {config.count_per_topic}")
    if config.seed:
        print(f"  Seed: {config.seed}")

    generator = CuttingEdgeGenerator()
    examples = generator.generate(config)

    print(f"\nGenerated {len(examples)} examples")

    # Save dataset
    output_path = Path(args.output)
    generator.save_dataset(examples, output_path)
    print(f"Saved to: {output_path}")

    # Validate if requested
    if args.validate:
        print("\nValidating dataset...")
        result = validate_dataset(output_path)

        if result.is_valid:
            print("✅ Validation PASSED")
            print(f"   Examples: {result.example_count}")
            print(f"   Validated: {result.validated_examples}")
            print(f"   Drafts: {result.draft_examples}")
        else:
            print("❌ Validation FAILED")
            for error in result.errors:
                print(f"   Error: {error}")
            sys.exit(1)

        if result.warnings:
            print("\nWarnings:")
            for warning in result.warnings:
                print(f"   - {warning}")

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
