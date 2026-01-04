"""Database layer.

This module provides the SQLAlchemy Base class for model definitions.

Note: AsyncSessionLocal, engine, and other session objects are intentionally
NOT re-exported here to avoid DATABASE_URL validation at import time.
Import them directly from app.db.session when needed at runtime.
"""

from app.db.base import Base
from app.db.bulk_operations import BulkOperations

__all__ = [
    "Base",
    "BulkOperations",
]
