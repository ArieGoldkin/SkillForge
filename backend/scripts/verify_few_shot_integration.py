#!/usr/bin/env python3
"""Manual verification script for few-shot integration.

This script connects to the real database and tests the few-shot system end-to-end:
- Verifies example data exists
- Tests semantic similarity search
- Displays quality scores and similarity distances
- Verifies token budget enforcement
- Tests with multiple agent types

Run this script manually to verify the integration:
    poetry run python scripts/verify_few_shot_integration.py
"""

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select, text

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.agent_example import AgentExample as AgentExampleModel
from app.shared.services.agents.few_shot_factory import (
    MAX_EXAMPLE_TOKENS,
    _estimate_token_count,
    _format_examples_for_prompt,
    _truncate_examples_to_budget,
    create_few_shot_agent,
)
from app.shared.services.embeddings.service import EmbeddingService
from app.shared.services.examples import SemanticExampleSelector

logger = get_logger(__name__)


async def verify_database_examples():
    """Verify agent_examples table has data."""
    print("\n" + "=" * 60)
    print("Step 1: Verifying Database Examples")
    print("=" * 60)

    async with AsyncSessionLocal() as session:
        # Count total examples
        result = await session.execute(text("SELECT COUNT(*) FROM agent_examples"))
        total_count = result.scalar()
        print(f"Total examples: {total_count}")

        # Count by agent type
        result = await session.execute(
            text(
                "SELECT agent_type, COUNT(*) as count "
                "FROM agent_examples "
                "GROUP BY agent_type "
                "ORDER BY count DESC"
            )
        )
        rows = result.all()

        print("\nExamples by Agent Type:")
        print(f"{'Agent Type':<30} {'Count':>10}")
        print("-" * 42)
        for agent_type, count in rows:
            print(f"{agent_type:<30} {count:>10}")

        # Check embeddings
        result = await session.execute(
            text("SELECT COUNT(*) FROM agent_examples WHERE embedding IS NULL")
        )
        null_embeddings = result.scalar()

        if null_embeddings == 0:
            print("\n✓ All examples have embeddings")
        else:
            print(f"\n✗ {null_embeddings} examples missing embeddings")

    return total_count > 0


async def test_semantic_search(agent_type: str, query: str):
    """Test semantic search for a specific query."""
    print(f"\n{'=' * 60}")
    print(f"Testing semantic search: {agent_type}")
    print(f"Query: {query}")
    print("=" * 60)

    embedding_service = EmbeddingService()

    async with AsyncSessionLocal() as session:
        selector = SemanticExampleSelector(session, embedding_service)

        # Test retrieval
        result = await selector.select_examples(
            content=query,
            agent_type=agent_type,
            max_examples=5,
            min_quality_score=0.7,
        )

        print(
            f"\nRetrieved {len(result.examples)} examples "
            f"from {result.total_candidates} candidates"
        )

        if result.avg_quality_score:
            print(f"Average quality: {result.avg_quality_score:.3f}")
        if result.avg_similarity_distance:
            print(f"Average similarity distance: {result.avg_similarity_distance:.3f}")

        # Display examples
        if result.examples:
            print("\nRetrieved Examples:")
            print(f"{'Rank':<6} {'Quality':<10} {'Relevance':<12} {'Input Summary':<60}")
            print("-" * 90)

            for i, example in enumerate(result.examples, 1):
                relevance = 1 - example.similarity_distance
                summary = example.input_summary[:55] + "..." if len(example.input_summary) > 55 else example.input_summary
                print(f"{i:<6} {example.quality_score:<10.2f} {relevance:<12.3f} {summary}")
        else:
            print("No examples found")

        return result


async def test_token_budget_enforcement():
    """Test that token budget is properly enforced."""
    print(f"\n{'=' * 60}")
    print("Step 3: Testing Token Budget Enforcement")
    print("=" * 60)
    print(f"Max tokens allowed: {MAX_EXAMPLE_TOKENS}")

    embedding_service = EmbeddingService()

    async with AsyncSessionLocal() as session:
        selector = SemanticExampleSelector(session, embedding_service)

        # Request many examples from research_analyst (has 61 examples)
        result = await selector.select_examples(
            content="Analyzing recent advances in machine learning architectures",
            agent_type="research_analyst",
            max_examples=20,  # Request many
            min_quality_score=0.7,
        )

        print(f"\nRequested: 20[/bold] examples")
        print(
            f"Retrieved: {len(result.examples)}[/bold] examples"
        )

        # Test truncation
        truncated = _truncate_examples_to_budget(result, MAX_EXAMPLE_TOKENS)
        print(
            f"After truncation: {len(truncated.examples)}[/bold] examples"
        )

        # Format and estimate tokens
        formatted = _format_examples_for_prompt(truncated)
        estimated_tokens = _estimate_token_count(formatted)
        print(
            f"Estimated tokens: {estimated_tokens}[/bold] "
            f"(limit: {MAX_EXAMPLE_TOKENS})"
        )

        if estimated_tokens <= MAX_EXAMPLE_TOKENS:
            print(
                "✓ Token budget respected"
            )
        else:
            print(
                f"✗ Token budget exceeded by {estimated_tokens - MAX_EXAMPLE_TOKENS}"
            )

        # Show formatted examples preview
        print("\nFormatted Prompt Preview:[/bold]")
        preview = formatted[:500] + "..." if len(formatted) > 500 else formatted
        print(f"{preview}")

        return estimated_tokens <= MAX_EXAMPLE_TOKENS


async def test_agent_creation_variants():
    """Test agent creation with control vs treatment variants."""
    print("\nStep 4: Testing Agent Creation Variants[/bold cyan]")

    embedding_service = EmbeddingService()

    # Mock agent factory
    def mock_factory(system_prompt: str = "", **kwargs):
        class MockAgent:
            def __init__(self, prompt):
                self.system_prompt = prompt
                self.created_at = datetime.now(UTC)

        return MockAgent(system_prompt)

    original_prompt = "You are a tech comparison agent specialized in analyzing frameworks."
    content = "Comparing React hooks vs Vue Composition API for state management"

    async with AsyncSessionLocal() as session:
        # Test control variant
        print("\nControl Variant (no examples):[/bold]")
        control_agent = await create_few_shot_agent(
            agent_type="tech_comparator",
            content=content,
            base_agent_factory=mock_factory,
            session=session,
            embedding_service=embedding_service,
            variant="control",
            system_prompt=original_prompt,
        )

        print(f"Prompt length: {len(control_agent.system_prompt)}[/bold] chars")
        has_examples = "FEW-SHOT EXAMPLES" in control_agent.system_prompt
        print(f"Has examples: {has_examples}[/bold]")

        # Test treatment variant
        print("\nTreatment Variant (with examples):[/bold]")
        treatment_agent = await create_few_shot_agent(
            agent_type="tech_comparator",
            content=content,
            base_agent_factory=mock_factory,
            session=session,
            embedding_service=embedding_service,
            variant="treatment",
            max_examples=3,
            system_prompt=original_prompt,
        )

        print(f"Prompt length: {len(treatment_agent.system_prompt)}[/bold] chars")
        has_examples = "FEW-SHOT EXAMPLES" in treatment_agent.system_prompt
        print(f"Has examples: {has_examples}[/bold]")

        if has_examples:
            example_count = treatment_agent.system_prompt.count("EXAMPLE ")
            print(f"Number of examples: {example_count}[/bold]")
            print("✓ Examples injected successfully")

            # Show diff in prompt length
            diff = len(treatment_agent.system_prompt) - len(control_agent.system_prompt)
            print(
                f"Prompt size increase: +{diff}[/bold] chars "
                f"(+{_estimate_token_count(treatment_agent.system_prompt) - _estimate_token_count(control_agent.system_prompt)}[/bold] tokens)"
            )
        else:
            print(
                "⚠ No examples found for this query"
            )

        return has_examples


async def test_multiple_agent_types():
    """Test few-shot with multiple agent types."""
    print("\nStep 5: Testing Multiple Agent Types[/bold cyan]")

    test_cases = [
        (
            "tech_comparator",
            "Comparing TypeScript vs JavaScript for large-scale applications",
        ),
        (
            "security_auditor",
            "Analyzing authentication security vulnerabilities in OAuth flows",
        ),
        (
            "implementation_planner",
            "Planning implementation of real-time notifications with WebSockets",
        ),
        (
            "performance_analyst",
            "Analyzing database query performance and indexing strategies",
        ),
        (
            "research_analyst",
            "Analyzing recent research on transformer architectures in NLP",
        ),
    ]

    results = []

    for agent_type, query in test_cases:
        result = await test_semantic_search(agent_type, query)
        results.append((agent_type, len(result.examples), result.total_candidates))
        await asyncio.sleep(0.5)  # Rate limiting

    # Summary table
    print("\nSummary by Agent Type:")
    print(f"{'Agent Type':<30} {'Retrieved':>10} {'Candidates':>12} {'Status':>8}")
    print("-" * 65)

    for agent_type, retrieved, candidates in results:
        status = "✓" if retrieved > 0 else "⚠"
        print(f"{agent_type:<30} {retrieved:>10} {candidates:>12} {status:>8}")


async def main():
    """Run all verification tests."""
    print("\nFew-Shot Integration Verification")
    print("=" * 60)

    try:
        # Step 1: Verify database
        db_ok = await verify_database_examples()
        if not db_ok:
            print("\n✗ Database verification failed")
            return

        # Step 2: Test semantic search for different agent types
        await test_multiple_agent_types()

        # Step 3: Test token budget
        budget_ok = await test_token_budget_enforcement()

        # Step 4: Test agent creation
        agent_ok = await test_agent_creation_variants()

        # Final summary
        print("\n" + "=" * 60)
        print("Verification Summary")
        print("=" * 60)
        print(f"Database: ✓")
        print(f"Token Budget: {'✓' if budget_ok else '✗'}")
        print(f"Agent Creation: {'✓' if agent_ok else '⚠'}")

        if db_ok and budget_ok:
            print("\n✓ Integration verification passed!")
        else:
            print("\n⚠ Some checks failed")

    except Exception as e:
        print(f"\nError: {e}")
        logger.exception("Verification failed")
        raise


if __name__ == "__main__":
    asyncio.run(main())
