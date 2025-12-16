"""Tutor schemas - COMPATIBILITY LAYER.

⚠️ DEPRECATED: This module is kept for backward compatibility during migration.
New code should import from app.domains.tutor.schemas instead.

This will be removed in Phase 9 after all imports are updated.
"""

# Re-export from new location for backward compatibility
from app.domains.tutor.schemas import *  # noqa: F403
