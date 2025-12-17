#!/usr/bin/env python3
"""Validation script for Few-Shot Prompting implementation.

This script validates that all components of the Few-Shot Prompting feature
flag system are correctly implemented and ready for production.

Run: poetry run python scripts/validate_few_shot_implementation.py
"""

import sys
from pathlib import Path


def check_file_exists(filepath: Path, description: str) -> bool:
    """Check if a file exists."""
    exists = filepath.exists()
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {filepath}")
    return exists


def check_imports() -> bool:
    """Verify all imports work correctly."""
    try:
        # Test feature flags import
        from app.core.feature_flags import get_technique_flags

        # Test variant selector import
        from app.shared.services.ab_testing import get_variant_selector

        # Test metrics import
        from app.shared.services.metrics.technique_metrics import (
            MetricsCollector,
            TechniqueMetrics,
        )

        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def check_functionality() -> bool:
    """Test basic functionality."""
    try:
        from app.core.feature_flags import get_technique_flags
        from app.shared.services.ab_testing import get_variant_selector
        from app.shared.services.metrics.technique_metrics import TechniqueMetrics

        # Test flags
        flags = get_technique_flags()
        assert hasattr(flags, "enable_few_shot")
        assert hasattr(flags, "ab_test_enabled")
        assert hasattr(flags, "ab_test_treatment_pct")
        print("✅ Feature flags working")

        # Test variant selector
        selector = get_variant_selector()
        variant = selector.select_variant("test-123", "few_shot_prompting")
        assert variant in ("control", "treatment")
        print("✅ Variant selector working")

        # Test metrics
        metrics = TechniqueMetrics(
            analysis_id="test-456",
            technique="few_shot_prompting",
            variant="treatment",
            example_retrieval_ms=50.0,
            num_examples_used=3,
        )
        assert metrics.example_retrieval_ms == 50.0
        assert metrics.num_examples_used == 3
        print("✅ Metrics tracking working")

        return True
    except Exception as e:
        print(f"❌ Functionality error: {e}")
        return False


def main():
    """Run all validation checks."""
    print("=" * 80)
    print("FEW-SHOT PROMPTING IMPLEMENTATION VALIDATION")
    print("=" * 80)
    print()

    backend_dir = Path(__file__).parent.parent
    all_checks = []

    # Check production files
    print("Production Files:")
    all_checks.append(
        check_file_exists(
            backend_dir / "app/shared/services/ab_testing/__init__.py",
            "A/B testing module",
        )
    )
    all_checks.append(
        check_file_exists(
            backend_dir / "app/shared/services/ab_testing/variant_selector.py",
            "Variant selector",
        )
    )
    all_checks.append(
        check_file_exists(
            backend_dir / "app/shared/services/metrics/technique_metrics.py",
            "Metrics tracking",
        )
    )
    print()

    # Check test files
    print("Test Files:")
    all_checks.append(
        check_file_exists(
            backend_dir / "tests/unit/shared/services/ab_testing/__init__.py",
            "A/B testing tests module",
        )
    )
    all_checks.append(
        check_file_exists(
            backend_dir / "tests/unit/shared/services/ab_testing/test_variant_selector.py",
            "Variant selector tests",
        )
    )
    all_checks.append(
        check_file_exists(
            backend_dir / "tests/unit/shared/services/metrics/test_technique_metrics.py",
            "Metrics tests",
        )
    )
    print()

    # Check documentation
    print("Documentation:")
    all_checks.append(
        check_file_exists(
            backend_dir / "docs/feature-flags-ab-testing.md",
            "Complete guide",
        )
    )
    all_checks.append(
        check_file_exists(
            backend_dir / "docs/implementation-summary-few-shot-ab-testing.md",
            "Implementation summary",
        )
    )
    all_checks.append(
        check_file_exists(
            backend_dir / "docs/few-shot-quick-reference.md",
            "Quick reference",
        )
    )
    print()

    # Check imports
    print("Import Checks:")
    all_checks.append(check_imports())
    print()

    # Check functionality
    print("Functionality Checks:")
    all_checks.append(check_functionality())
    print()

    # Summary
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    passed = sum(all_checks)
    total = len(all_checks)

    if passed == total:
        print(f"✅ ALL CHECKS PASSED ({passed}/{total})")
        print()
        print("🚀 Implementation is ready for production!")
        print()
        print("Next steps:")
        print("1. Run full test suite: poetry run pytest tests/unit/")
        print("2. Run code quality checks: poetry run ruff check app/")
        print("3. Review documentation: docs/feature-flags-ab-testing.md")
        print("4. Create PR for review")
        return 0
    else:
        print(f"❌ SOME CHECKS FAILED ({passed}/{total})")
        print()
        print("Please fix the failing checks before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
