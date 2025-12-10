"""Fixture loader for retrieval smoke tests.

Loads test documents and queries from JSON fixtures for deterministic,
reproducible smoke tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict


class Section(TypedDict):
    """Document section structure."""

    id: str
    title: str
    content: str
    granularity: str


class Document(TypedDict):
    """Test document structure."""

    id: str
    title: str
    content_type: str
    bucket: str
    language: str
    tags: list[str]
    sections: list[Section]


class Query(TypedDict):
    """Test query structure."""

    id: str
    query: str
    modes: list[str]
    category: str
    expected_chunks: list[str]
    min_score: float | None
    max_score: float | None
    description: str


class FixtureData(TypedDict):
    """Complete fixture data structure."""

    version: str
    documents: list[Document]


class QueryData(TypedDict):
    """Query fixture data structure."""

    version: str
    queries: list[Query]


class FixtureLoader:
    """Load and manage test fixtures for smoke tests."""

    def __init__(self, fixtures_dir: Path | None = None) -> None:
        """Initialize fixture loader.

        Args:
            fixtures_dir: Directory containing fixture JSON files.
                         Defaults to the fixtures directory adjacent to this file.

        """
        self.fixtures_dir = fixtures_dir or Path(__file__).parent

    def load_documents(self) -> list[Document]:
        """Load test documents from JSON fixture.

        Returns:
            List of Document dictionaries.

        Raises:
            FileNotFoundError: If documents.json doesn't exist.

        """
        path = self.fixtures_dir / "documents.json"
        with path.open() as f:
            data: FixtureData = json.load(f)
        return data["documents"]

    def load_queries(self) -> list[Query]:
        """Load test queries from JSON fixture.

        Returns:
            List of Query dictionaries with expected results.

        Raises:
            FileNotFoundError: If queries.json doesn't exist.

        """
        path = self.fixtures_dir / "queries.json"
        with path.open() as f:
            data: QueryData = json.load(f)
        return data["queries"]

    def get_queries_for_mode(self, mode: str) -> list[Query]:
        """Filter queries that support a specific search mode.

        Args:
            mode: Search mode ('semantic', 'keyword', 'hybrid').

        Returns:
            Queries that include the specified mode.

        """
        return [q for q in self.load_queries() if mode in q["modes"]]

    def get_queries_by_category(self, category: str) -> list[Query]:
        """Filter queries by test category.

        Args:
            category: Query category ('specific', 'broad', 'negative', 'edge').

        Returns:
            Queries matching the category.

        """
        return [q for q in self.load_queries() if q["category"] == category]

    def get_documents_by_bucket(self, bucket: str) -> list[Document]:
        """Filter documents by size bucket.

        Args:
            bucket: Document bucket ('short', 'long').

        Returns:
            Documents in the specified bucket.

        """
        return [d for d in self.load_documents() if d["bucket"] == bucket]

    def get_document_by_id(self, doc_id: str) -> Document | None:
        """Get a specific document by ID.

        Args:
            doc_id: Document identifier.

        Returns:
            Document if found, None otherwise.

        """
        for doc in self.load_documents():
            if doc["id"] == doc_id:
                return doc
        return None

    def validate(self) -> list[str]:
        """Validate fixture integrity.

        Checks that:
        - All documents have required fields
        - All queries reference valid document sections
        - No duplicate IDs

        Returns:
            List of validation errors (empty if valid).

        """
        errors: list[str] = []
        documents = self.load_documents()
        queries = self.load_queries()

        # Build set of valid section IDs
        section_ids: set[str] = set()
        doc_ids: set[str] = set()

        for doc in documents:
            if doc["id"] in doc_ids:
                errors.append(f"Duplicate document ID: {doc['id']}")
            doc_ids.add(doc["id"])

            if doc.get("bucket") not in ("short", "long"):
                errors.append(f"Invalid bucket for {doc['id']}: {doc.get('bucket')}")

            for section in doc.get("sections", []):
                section_ids.add(section["id"])

        # Validate queries reference valid sections
        query_ids: set[str] = set()
        for query in queries:
            if query["id"] in query_ids:
                errors.append(f"Duplicate query ID: {query['id']}")
            query_ids.add(query["id"])

            for chunk_id in query.get("expected_chunks", []):
                if chunk_id not in section_ids:
                    errors.append(f"Query {query['id']} references unknown section: {chunk_id}")

        return errors
