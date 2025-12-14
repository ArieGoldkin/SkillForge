# Embedding Pipeline Reference Architecture

**Status:** ✅ COMPLETE
**Version:** 1.0.0
**Last Updated:** 2025-12-13
**Maintainer:** SkillForge Team

---

```yaml
# AI Agent Metadata - Machine-parseable configuration
document_type: reference_architecture
domain: embedding_pipeline
version: "1.0.0"
compatibility:
  min_python: "3.11"
  embedding_model: "text-embedding-3-small"
  embedding_dimensions: 1536
  database: "postgresql+pgvector"
audiences:
  - engineers
  - ai_agents
  - product_managers
  - data_evaluators
sections:
  quick_evaluation: "section-2"
  implementation: "section-5"
  quality_gates: "section-6"
  ai_metadata: "appendix-d"
```

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Quick Start Checklist](#2-quick-start-checklist)
3. [Data Assessment Framework](#3-data-assessment-framework)
4. [Pipeline Architecture](#4-pipeline-architecture)
5. [Step-by-Step Implementation Guide](#5-step-by-step-implementation-guide)
6. [Quality Gates & Testing](#6-quality-gates--testing)
7. [Cost Analysis](#7-cost-analysis)
8. [Extension Points](#8-extension-points)
9. [Troubleshooting & FAQs](#9-troubleshooting--faqs)
10. [Appendices](#10-appendices)

---

## 1. Executive Summary

### 1.1 Purpose

This document provides a comprehensive reference architecture for embedding text-based content (wellness articles, coaching transcripts, Q&A pairs) into vector representations for semantic search and retrieval. It serves as:

- **Implementation Guide**: Step-by-step instructions for engineering teams
- **Evaluation Reference**: Structured criteria for AI agents and stakeholders
- **Extensible Framework**: Foundation for future data types

### 1.2 Key Metrics at a Glance

| Metric | Value | Notes |
|--------|-------|-------|
| Embedding Model | `text-embedding-3-small` | OpenAI, 1536 dimensions |
| Max Tokens/Chunk | 7,500 | Below 8,191 API limit |
| Target Recall@5 | ≥ 70% | Quality gate threshold |
| Typical Latency | < 500ms | 95th percentile |
| Cost per 1K docs | ~$0.03 | At 1,500 tokens/doc avg |

### 1.3 Prerequisites

- Python 3.11+
- PostgreSQL 15+ with pgvector extension
- OpenAI API key with embedding access
- Docker (for local development)

### 1.4 Expected Outcomes

After following this guide, you will have:
1. A validated dataset ready for embedding
2. Chunked content with appropriate granularity
3. Stored embeddings in PostgreSQL with HNSW indexing
4. Working semantic search with quality metrics

---

## 2. Quick Start Checklist

Use this checklist to quickly assess whether your data is ready for embedding. Each phase must pass before proceeding.

### 2.1 Phase 1: Data Compatibility (Required)

| Check | Criteria | Pass/Fail |
|-------|----------|-----------|
| Text-based | Content is plain text (not binary, images, audio) | [ ] |
| UTF-8 encoded | All files use UTF-8 encoding | [ ] |
| Token range | Documents are 10 - 100,000 characters | [ ] |
| Structured format | Data is in JSON, CSV, or similar parseable format | [ ] |
| Content identifiers | Each document has a unique `content_id` | [ ] |

**Minimum requirement:** All checks must pass.

### 2.2 Phase 2: Privacy & Compliance (Critical)

| Check | Criteria | Pass/Fail |
|-------|----------|-----------|
| PII scan complete | Ran automated PII detection (regex + NER) | [ ] |
| PII removed/redacted | All detected PII has been handled | [ ] |
| Health data review | PHI considerations addressed (if applicable) | [ ] |
| Data retention policy | Retention period defined | [ ] |
| Consent verification | Data collection consent confirmed | [ ] |

**Minimum requirement:** First 3 checks must pass before embedding.

### 2.3 Phase 3: Quality Requirements (Recommended)

| Check | Criteria | Pass/Fail |
|-------|----------|-----------|
| Ground truth queries | At least 20 test queries with expected results | [ ] |
| Content diversity | Multiple content types represented | [ ] |
| Language consistency | Primary language identified | [ ] |
| Deduplication check | No duplicate documents | [ ] |

**Minimum requirement:** Ground truth queries available for evaluation.

### 2.4 AI Agent Evaluation Format

For automated evaluation by AI agents (Claude Code, etc.), use this JSON structure:

```json
{
  "evaluation_id": "eval-2025-12-13-001",
  "dataset_name": "health_coaching_v1",
  "phase_1_data_compatibility": {
    "text_based": true,
    "utf8_encoded": true,
    "token_range_valid": true,
    "structured_format": "json",
    "has_content_ids": true,
    "pass": true
  },
  "phase_2_privacy": {
    "pii_scan_complete": true,
    "pii_removed": true,
    "health_data_reviewed": true,
    "retention_policy_defined": true,
    "consent_verified": true,
    "pass": true
  },
  "phase_3_quality": {
    "ground_truth_query_count": 50,
    "content_types": ["article", "transcript", "qa_pair"],
    "primary_language": "en",
    "duplicate_count": 0,
    "pass": true
  },
  "overall_recommendation": "PROCEED",
  "notes": "Dataset meets all requirements for embedding"
}
```

---

## 3. Data Assessment Framework

### 3.1 Content Type Compatibility Matrix

| Data Type | Embeddability | Chunking Strategy | Typical Token Range | Notes |
|-----------|---------------|-------------------|---------------------|-------|
| Wellness Articles | ✅ Excellent | Hierarchical (coarse→fine) | 500 - 5,000 | Structured headings |
| Coaching Transcripts | ✅ Good | Conversational turns (3-5 exchanges) | 1,000 - 10,000 | Speaker attribution |
| Q&A Pairs | ✅ Excellent | Question+Answer single chunk | 100 - 500 | High precision |
| Medical Notes (SOAP) | ⚠️ Requires PII Scrubbing | Section-based (S/O/A/P) | 200 - 1,000 | PHI considerations |
| Research Papers | ✅ Good | Section + paragraph | 5,000 - 50,000 | Abstract priority |
| Biometric Data | ❌ Not Suitable | N/A | N/A | Use time-series DB |
| Audio/Video | ❌ Not Suitable | N/A | N/A | Transcribe first |

### 3.2 Decision Tree

```
START: Is your data text-based?
│
├─ NO → ❌ Cannot embed. Convert to text first (transcription, OCR).
│
└─ YES → Does it contain PII/PHI?
         │
         ├─ YES → Can PII be removed/redacted?
         │        │
         │        ├─ YES → Scrub PII → Continue to Structure check
         │        │
         │        └─ NO → ❌ Cannot embed without privacy violation.
         │
         └─ NO → Continue to Structure check

STRUCTURE CHECK: Is content structured (JSON, headings, sections)?
│
├─ YES → Use hierarchical chunking (coarse → fine)
│
└─ NO → Is it conversational (dialogue, transcript)?
         │
         ├─ YES → Use conversational chunking (group turns)
         │
         └─ NO → Use sliding window chunking with overlap

TOKEN CHECK: Average tokens per document?
│
├─ < 500 tokens → Embed as single chunk (no splitting)
│
├─ 500 - 7,500 tokens → Standard chunking applies
│
└─ > 7,500 tokens → Must split into multiple chunks
```

### 3.3 Structural Requirements

#### Required Fields

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "EmbeddableContent",
  "type": "object",
  "required": ["content_id", "text", "content_type"],
  "properties": {
    "content_id": {
      "type": "string",
      "description": "Unique identifier for this content",
      "pattern": "^[a-zA-Z0-9_-]+$"
    },
    "text": {
      "type": "string",
      "minLength": 10,
      "maxLength": 500000,
      "description": "The text content to embed"
    },
    "content_type": {
      "type": "string",
      "enum": ["article", "transcript", "qa_pair", "research_paper", "medical_note", "other"],
      "description": "Type of content for chunking strategy selection"
    },
    "metadata": {
      "type": "object",
      "properties": {
        "title": { "type": "string" },
        "author": { "type": "string" },
        "created_at": { "type": "string", "format": "date-time" },
        "language": { "type": "string", "default": "en" },
        "tags": { "type": "array", "items": { "type": "string" } },
        "source": { "type": "string" },
        "has_pii": { "type": "boolean", "default": false }
      }
    }
  }
}
```

#### Example: Wellness Article

```json
{
  "content_id": "wellness-nutrition-001",
  "text": "# Understanding Balanced Nutrition\n\nA balanced diet is essential for maintaining good health...",
  "content_type": "article",
  "metadata": {
    "title": "Understanding Balanced Nutrition",
    "author": "Health Coach Team",
    "created_at": "2025-01-15T10:00:00Z",
    "language": "en",
    "tags": ["nutrition", "wellness", "diet"],
    "source": "internal_knowledge_base",
    "has_pii": false
  }
}
```

#### Example: Coaching Transcript

```json
{
  "content_id": "coaching-session-2025-001",
  "text": "Coach: Good morning! How have you been feeling this week?\nClient: I've been struggling with my sleep schedule...",
  "content_type": "transcript",
  "metadata": {
    "title": "Sleep Improvement Session",
    "created_at": "2025-01-20T14:30:00Z",
    "language": "en",
    "tags": ["sleep", "wellness", "coaching"],
    "source": "coaching_platform",
    "has_pii": false
  }
}
```

### 3.4 Privacy Considerations

#### 3.4.1 Three-Level PII Detection

**Level 1: Regex Patterns (Fast, High Precision)**

```python
PII_PATTERNS = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "phone_us": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
    "date_of_birth": r"\b(0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])[-/](19|20)\d{2}\b",
    "ip_address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
}
```

**Level 2: Named Entity Recognition (NER)**

```python
# Using spaCy for NER-based PII detection
import spacy

nlp = spacy.load("en_core_web_sm")

def detect_ner_pii(text: str) -> list[dict]:
    """Detect person names, locations, organizations."""
    doc = nlp(text)
    pii_entities = []
    for ent in doc.ents:
        if ent.label_ in ["PERSON", "GPE", "LOC", "ORG"]:
            pii_entities.append({
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char
            })
    return pii_entities
```

**Level 3: Manual Review (Required for Health Data)**

For health coaching data, manually review a sample of 100 documents to identify:
- Medical conditions mentioned
- Treatment details
- Provider names
- Appointment dates/times

#### 3.4.2 PII Redaction Strategy

```python
def redact_pii(text: str, pii_detections: list[dict]) -> str:
    """Replace PII with type-specific placeholders."""
    REDACTION_MAP = {
        "email": "[EMAIL_REDACTED]",
        "phone_us": "[PHONE_REDACTED]",
        "ssn": "[SSN_REDACTED]",
        "PERSON": "[NAME_REDACTED]",
        "GPE": "[LOCATION_REDACTED]",
    }

    # Sort by position descending to preserve indices
    sorted_detections = sorted(pii_detections, key=lambda x: x["start"], reverse=True)

    for detection in sorted_detections:
        pii_type = detection.get("label") or detection.get("type")
        placeholder = REDACTION_MAP.get(pii_type, "[REDACTED]")
        text = text[:detection["start"]] + placeholder + text[detection["end"]:]

    return text
```

#### 3.4.3 Health Data Sensitivity Guidelines

| Data Category | Sensitivity | Handling |
|---------------|-------------|----------|
| General wellness tips | Low | No special handling |
| Diet/exercise plans | Low | No special handling |
| Sleep patterns | Medium | Anonymize identifiers |
| Mental health mentions | High | Require explicit consent |
| Medical diagnoses | Critical | PHI - require HIPAA compliance |
| Prescription information | Critical | PHI - require HIPAA compliance |

---

## 4. Pipeline Architecture

### 4.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        EMBEDDING PIPELINE ARCHITECTURE                       │
└─────────────────────────────────────────────────────────────────────────────┘

   DATA SOURCE                                                    RETRIEVAL
       │                                                              ▲
       ▼                                                              │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐
│   INGEST    │───▶│  PII SCRUB  │───▶│    CHUNK    │───▶│       EMBED         │
│             │    │             │    │             │    │                     │
│ • Validate  │    │ • Regex     │    │ • Coarse    │    │ • OpenAI API        │
│ • Parse     │    │ • NER       │    │ • Fine      │    │ • 1536 dimensions   │
│ • Normalize │    │ • Redact    │    │ • Overlap   │    │ • L2 normalize      │
└─────────────┘    └─────────────┘    └─────────────┘    └──────────┬──────────┘
                                                                    │
                                                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              STORAGE LAYER                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    PostgreSQL + pgvector                             │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │    │
│  │  │ analysis_    │  │ HNSW Index   │  │ GIN Index    │               │    │
│  │  │ chunks       │  │ (semantic)   │  │ (keyword)    │               │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SEARCH LAYER                                    │
│                                                                              │
│    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                    │
│    │  SEMANTIC   │    │   KEYWORD   │    │   HYBRID    │                    │
│    │  (kNN)      │    │  (tsvector) │    │   (RRF)     │                    │
│    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                    │
│           │                  │                  │                            │
│           └──────────────────┼──────────────────┘                            │
│                              ▼                                               │
│                       ┌─────────────┐                                        │
│                       │  RE-RANK    │                                        │
│                       │  (optional) │                                        │
│                       └──────┬──────┘                                        │
│                              │                                               │
└──────────────────────────────┼───────────────────────────────────────────────┘
                               │
                               ▼
                         SEARCH RESULTS
```

### 4.2 Component Breakdown

| Stage | Input | Process | Output | Error Handling |
|-------|-------|---------|--------|----------------|
| **Ingest** | Raw files (JSON, CSV) | Validate UTF-8, schema, size | Normalized JSON | Reject invalid, log errors |
| **PII Scrub** | Text content | Regex + NER detection | Redacted text + PII log | Flag for manual review |
| **Chunk** | Clean text | Hierarchical split, overlap | `ChunkText` objects | Truncate > 7500 tokens |
| **Embed** | Chunks | Batch OpenAI API call | 1536-dim vectors | 3x retry with backoff |
| **Store** | Vectors + metadata | PostgreSQL INSERT | Persisted chunks | FK validation, rollback |
| **Search** | Query text | Embed + kNN/keyword/hybrid | Ranked results | Empty results = valid |

### 4.3 Data Flow Example

```python
# Example: Processing a wellness article

# 1. INGEST
raw_data = {
    "content_id": "wellness-001",
    "text": "# Sleep Hygiene Tips\n\nGetting quality sleep is essential...",
    "content_type": "article"
}

# 2. PII SCRUB (already clean in this example)
clean_text = raw_data["text"]

# 3. CHUNK
from app.services.chunking.chunker import chunk_document

coarse_chunks, fine_chunks = chunk_document(
    text=clean_text,
    short_window=900,
    long_window=600,
    overlap_pct=0.12
)
# Result: 3 coarse chunks, 8 fine chunks

# 4. EMBED
from app.services.embeddings import EmbeddingService

service = EmbeddingService()
embeddings = []
for chunk in coarse_chunks + fine_chunks:
    vector = await service.generate_embedding(chunk.text, normalize=True)
    embeddings.append((chunk, vector))

# 5. STORE
from app.db.repositories.chunk_repository import ChunkRepository

repo = ChunkRepository(session)
await repo.create_many([
    {
        "analysis_id": analysis_id,
        "granularity": chunk.granularity,
        "path": chunk.path,
        "snippet": chunk.text[:200],
        "vector": vector,
        "hash": chunk.content_hash,
    }
    for chunk, vector in embeddings
])

# 6. SEARCH
results = await repo.hybrid_search(
    query_embedding=await service.generate_embedding("how to sleep better"),
    query_text="how to sleep better",
    limit=5
)
```

---

## 5. Step-by-Step Implementation Guide

### 5.1 Environment Setup

#### 5.1.1 Prerequisites Installation

```bash
# Clone repository (if applicable)
cd /path/to/project/backend

# Install Python dependencies
poetry install

# Set up environment variables
cat > .env << 'EOF'
# Required
OPENAI_API_KEY=sk-your-key-here
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/skillforge

# Optional
ENVIRONMENT=development
LOG_LEVEL=INFO
METRICS_ENABLED=true
BATCH_SIZE_MIN=10
BATCH_SIZE_MAX=100
EOF

# Start PostgreSQL with pgvector
docker compose up -d postgres

# Wait for database to be ready
sleep 5

# Run database migrations
poetry run alembic upgrade head

# Verify setup
poetry run python -c "
from app.services.embeddings import EmbeddingService
import asyncio

async def verify():
    service = EmbeddingService()
    embedding = await service.generate_embedding('test', normalize=True)
    print(f'Setup verified! Embedding dimensions: {len(embedding)}')
    await service.close()

asyncio.run(verify())
"
```

#### 5.1.2 Verify pgvector Extension

```sql
-- Connect to database and verify
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Should return one row with 'vector' extension
```

### 5.2 Data Preparation

#### 5.2.1 Example: Wellness Article Processing

```python
"""
Complete example: Processing a wellness article from raw input to stored embeddings.

Location: backend/scripts/embed_wellness_article.py
"""

import asyncio
import json
from pathlib import Path

from app.core.config import settings
from app.db.session import async_session_maker
from app.services.chunking.chunker import chunk_document
from app.services.embeddings import EmbeddingService
from app.services.pii.detector import PIIDetector
from app.db.repositories.chunk_repository import ChunkRepository


async def process_wellness_article(input_path: str, analysis_id: str):
    """Process a single wellness article through the embedding pipeline."""

    # 1. Load and validate input
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    assert "content_id" in data, "Missing required field: content_id"
    assert "text" in data, "Missing required field: text"
    assert len(data["text"]) >= 10, "Text too short (min 10 chars)"

    print(f"Processing: {data['content_id']}")
    print(f"Text length: {len(data['text'])} chars")

    # 2. PII Detection and Scrubbing
    detector = PIIDetector()
    pii_results = detector.scan(data["text"])

    if pii_results.has_pii:
        print(f"WARNING: PII detected - {len(pii_results.detections)} instances")
        clean_text = detector.redact(data["text"], pii_results.detections)
    else:
        print("No PII detected")
        clean_text = data["text"]

    # 3. Chunking
    coarse_chunks, fine_chunks = chunk_document(
        text=clean_text,
        short_window=900,
        long_window=600,
        overlap_pct=0.12,
        max_tokens=7500,
    )

    print(f"Created {len(coarse_chunks)} coarse chunks, {len(fine_chunks)} fine chunks")

    # 4. Embedding Generation
    embedding_service = EmbeddingService()
    all_chunks = coarse_chunks + fine_chunks

    try:
        embeddings_with_metadata = []

        for i, chunk in enumerate(all_chunks):
            vector = await embedding_service.generate_embedding(
                text=chunk.text,
                normalize=True
            )

            embeddings_with_metadata.append({
                "analysis_id": analysis_id,
                "granularity": chunk.granularity,
                "path": chunk.path,
                "section_title": chunk.section_title,
                "chunk_idx": chunk.chunk_idx,
                "chunk_total": chunk.chunk_total,
                "content_type": data.get("content_type", "article"),
                "language": data.get("metadata", {}).get("language", "en"),
                "hash": chunk.content_hash,
                "model": embedding_service.model,
                "model_version": "v1",
                "snippet": chunk.text[:200],
                "vector": vector,
                "token_count": chunk.token_count,
                "was_truncated": chunk.was_truncated,
            })

            if (i + 1) % 10 == 0:
                print(f"Embedded {i + 1}/{len(all_chunks)} chunks")

        # 5. Store in Database
        async with async_session_maker() as session:
            repo = ChunkRepository(session)
            created = await repo.create_many(embeddings_with_metadata)
            await session.commit()

            print(f"Stored {len(created)} chunks in database")

        return {
            "content_id": data["content_id"],
            "chunks_created": len(created),
            "coarse_count": len(coarse_chunks),
            "fine_count": len(fine_chunks),
            "pii_detected": pii_results.has_pii,
        }

    finally:
        await embedding_service.close()


# Run the pipeline
if __name__ == "__main__":
    import uuid

    result = asyncio.run(process_wellness_article(
        input_path="data/wellness_article.json",
        analysis_id=str(uuid.uuid4())
    ))

    print(f"\nResult: {json.dumps(result, indent=2)}")
```

#### 5.2.2 Example: Coaching Transcript Processing

```python
"""
Complete example: Processing a coaching transcript with conversational chunking.

Key difference: Transcripts use turn-based chunking (3-5 exchanges per chunk)
to preserve conversational context.

Location: backend/scripts/embed_coaching_transcript.py
"""

import asyncio
import json
import re
from dataclasses import dataclass


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""
    speaker: str
    text: str
    turn_idx: int


def parse_transcript(text: str) -> list[ConversationTurn]:
    """Parse a transcript into individual turns."""
    # Pattern: "Speaker: text" or "Speaker - text"
    pattern = r'^([\w\s]+)[:\-]\s*(.+)$'

    turns = []
    for idx, line in enumerate(text.strip().split('\n')):
        line = line.strip()
        if not line:
            continue

        match = re.match(pattern, line)
        if match:
            turns.append(ConversationTurn(
                speaker=match.group(1).strip(),
                text=match.group(2).strip(),
                turn_idx=idx
            ))
        else:
            # Continuation of previous turn
            if turns:
                turns[-1].text += " " + line

    return turns


def chunk_transcript(turns: list[ConversationTurn], turns_per_chunk: int = 4) -> list[dict]:
    """
    Chunk transcript into groups of conversational turns.

    Args:
        turns: List of conversation turns
        turns_per_chunk: Number of turns to group (default: 4)

    Returns:
        List of chunk dictionaries with text and metadata
    """
    chunks = []

    for i in range(0, len(turns), turns_per_chunk):
        chunk_turns = turns[i:i + turns_per_chunk]

        # Combine turns into chunk text
        chunk_text = "\n".join([
            f"{turn.speaker}: {turn.text}"
            for turn in chunk_turns
        ])

        chunks.append({
            "text": chunk_text,
            "granularity": "coarse",
            "path": ["transcript", f"segment-{i // turns_per_chunk}"],
            "chunk_idx": i // turns_per_chunk,
            "chunk_total": (len(turns) + turns_per_chunk - 1) // turns_per_chunk,
            "start_turn": chunk_turns[0].turn_idx,
            "end_turn": chunk_turns[-1].turn_idx,
            "speakers": list(set(t.speaker for t in chunk_turns)),
        })

    return chunks


async def process_transcript(input_path: str, analysis_id: str):
    """Process a coaching transcript through the embedding pipeline."""

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Parse transcript into turns
    turns = parse_transcript(data["text"])
    print(f"Parsed {len(turns)} conversation turns")

    # Chunk into groups of 4 turns
    chunks = chunk_transcript(turns, turns_per_chunk=4)
    print(f"Created {len(chunks)} chunks")

    # Continue with embedding and storage (same as wellness article)...
    # [embedding code omitted for brevity - same pattern as 5.2.1]

    return {"chunks_created": len(chunks)}


# Example transcript format:
EXAMPLE_TRANSCRIPT = """
Coach: Good morning! How have you been feeling this week?
Client: I've been struggling with my sleep schedule lately.
Coach: I'm sorry to hear that. Can you tell me more about what's been happening?
Client: I keep waking up at 3 AM and can't fall back asleep.
Coach: That's a common issue. Let's explore some strategies that might help.
Client: That would be great. I'm willing to try anything at this point.
Coach: First, let's talk about your evening routine. What do you typically do before bed?
Client: Usually I watch TV or scroll through my phone until I feel tired.
"""
```

### 5.3 Embedding Generation

#### 5.3.1 Best Practices

```python
"""
Embedding generation best practices and patterns.
"""

from app.services.embeddings import EmbeddingService

# ✅ DO: Use batch processing for multiple texts
async def embed_batch_correct(texts: list[str]) -> list[list[float]]:
    """Efficient batch embedding."""
    service = EmbeddingService()
    try:
        results = await service.generate_embeddings_batch(
            texts=texts,
            normalize=True,
            batch_size=50  # Process 50 at a time
        )
        return [vector for vector, _latency in results]
    finally:
        await service.close()


# ❌ DON'T: Embed one at a time in a loop (10x slower)
async def embed_batch_wrong(texts: list[str]) -> list[list[float]]:
    """Inefficient one-at-a-time embedding."""
    service = EmbeddingService()
    results = []
    for text in texts:  # Bad: sequential API calls
        vector = await service.generate_embedding(text)
        results.append(vector)
    await service.close()
    return results


# ✅ DO: Use content hash for deduplication
from app.services.chunking.dedup import compute_chunk_hash

def should_embed(text: str, existing_hashes: set[str], model: str, version: str) -> bool:
    """Check if content needs embedding (not already in database)."""
    chunk_hash = compute_chunk_hash(text, model, version)
    return chunk_hash not in existing_hashes


# ✅ DO: Handle rate limits gracefully (built into service)
# The EmbeddingService automatically handles:
# - Rate limiting with backpressure
# - Exponential backoff on 429 errors
# - Adaptive batch sizing

# ✅ DO: Close the service when done
async def proper_cleanup():
    """Always close the service to release resources."""
    service = EmbeddingService()
    try:
        # ... do work ...
        pass
    finally:
        await service.close()  # Important!
```

#### 5.3.2 Performance Optimization

| Optimization | Impact | Implementation |
|--------------|--------|----------------|
| Batch processing | 50% faster | Use `generate_embeddings_batch()` |
| Content deduplication | 20-40% cost savings | Check hash before embedding |
| Adaptive batch sizing | Auto-adjusts | Built into service (backpressure) |
| Connection pooling | Reduced latency | AsyncOpenAI client handles this |
| Parallel chunking | Faster preprocessing | Process chunks in parallel before embedding |

### 5.4 Storage & Indexing

#### 5.4.1 Database Schema

```sql
-- Core table for storing chunks with embeddings
CREATE TABLE analysis_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,

    -- Chunking metadata
    granularity VARCHAR(20) NOT NULL CHECK (granularity IN ('coarse', 'fine', 'summary')),
    path JSONB NOT NULL,  -- Hierarchical path: ["doc_id", "section_id"]
    section_title TEXT,
    chunk_idx INTEGER NOT NULL CHECK (chunk_idx >= 0),
    chunk_total INTEGER NOT NULL CHECK (chunk_total > 0),

    -- Content metadata
    content_type VARCHAR(50),
    language VARCHAR(20),

    -- Deduplication
    hash VARCHAR(128) NOT NULL,

    -- Embedding metadata
    model VARCHAR(100),
    model_version VARCHAR(50),

    -- Content preview
    snippet TEXT,

    -- Vector embedding (1536 dimensions for text-embedding-3-small)
    vector vector(1536) NOT NULL,

    -- Full-text search
    content_tsvector TSVECTOR,

    -- Telemetry
    token_count INTEGER,
    embedding_latency_ms FLOAT,
    was_truncated BOOLEAN DEFAULT FALSE,

    -- PII tracking
    pii_flag BOOLEAN DEFAULT FALSE,
    pii_types JSONB,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

    -- Constraints
    CONSTRAINT chk_chunk_idx_lt_total CHECK (chunk_idx < chunk_total)
);

-- HNSW index for fast semantic search
CREATE INDEX ix_analysis_chunks_vector_hnsw
ON analysis_chunks
USING hnsw (vector vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- GIN index for keyword search
CREATE INDEX ix_analysis_chunks_tsvector
ON analysis_chunks
USING gin (content_tsvector);

-- B-tree indexes for filtering
CREATE INDEX ix_analysis_chunks_analysis_id ON analysis_chunks(analysis_id);
CREATE INDEX ix_analysis_chunks_hash ON analysis_chunks(hash);
CREATE INDEX ix_analysis_chunks_content_type ON analysis_chunks(content_type);
CREATE INDEX ix_analysis_chunks_granularity ON analysis_chunks(granularity);
```

#### 5.4.2 HNSW Index Tuning

| Parameter | Default | Recommended | Description |
|-----------|---------|-------------|-------------|
| `m` | 16 | 16-32 | Connections per node (higher = better recall, more memory) |
| `ef_construction` | 64 | 64-128 | Build-time accuracy (higher = slower build, better index) |
| `ef_search` | 40 | 40-100 | Query-time accuracy (set at query time) |

```sql
-- For higher recall (slower queries, better accuracy)
SET hnsw.ef_search = 100;

-- For faster queries (lower recall)
SET hnsw.ef_search = 40;

-- Verify index is being used
EXPLAIN ANALYZE
SELECT id, snippet, 1 - (vector <=> '[0.1, 0.2, ...]'::vector) as similarity
FROM analysis_chunks
ORDER BY vector <=> '[0.1, 0.2, ...]'::vector
LIMIT 10;
-- Should show: "Index Scan using ix_analysis_chunks_vector_hnsw"
```

### 5.5 Search & Retrieval

#### 5.5.1 Search Modes

```python
"""
Three search modes available in the SearchService.
"""

from app.services.search.search_service import SearchService
from app.schemas.search import SearchMode, SearchFilters

# Initialize service
search_service = SearchService(session, embedding_service)

# 1. SEMANTIC SEARCH (vector similarity)
# Best for: Conceptual queries, synonyms, paraphrases
semantic_results = await search_service.search(
    query="How can I improve my sleep quality?",
    mode=SearchMode.SEMANTIC,
    top_k=10,
)

# 2. KEYWORD SEARCH (full-text)
# Best for: Exact terms, technical jargon, names
keyword_results = await search_service.search(
    query="melatonin circadian rhythm",
    mode=SearchMode.KEYWORD,
    top_k=10,
)

# 3. HYBRID SEARCH (semantic + keyword with RRF fusion)
# Best for: General queries, balances precision and recall
hybrid_results = await search_service.search(
    query="tips for better sleep hygiene",
    mode=SearchMode.HYBRID,
    top_k=10,
)

# With filters
filtered_results = await search_service.search(
    query="nutrition advice",
    mode=SearchMode.HYBRID,
    top_k=10,
    filters=SearchFilters(
        content_type="article",
        analysis_id="specific-analysis-uuid"
    )
)
```

#### 5.5.2 Coarse-to-Fine Retrieval

```python
"""
Two-stage retrieval for hierarchical content.

Stage 1: Find relevant sections (coarse chunks)
Stage 2: Find specific paragraphs within those sections (fine chunks)
"""

async def coarse_to_fine_search(query: str, top_sections: int = 3, top_paragraphs: int = 5):
    """
    Two-stage retrieval: sections first, then paragraphs.
    """

    # Stage 1: Find relevant coarse chunks (sections)
    coarse_results = await search_service.search(
        query=query,
        mode=SearchMode.SEMANTIC,
        top_k=top_sections,
        filters=SearchFilters(granularity="coarse")  # Custom filter
    )

    # Extract section paths
    section_paths = [r.metadata.path for r in coarse_results]

    # Stage 2: Find fine chunks within those sections
    fine_results = []
    for path in section_paths:
        section_fine = await search_service.search(
            query=query,
            mode=SearchMode.SEMANTIC,
            top_k=top_paragraphs,
            filters=SearchFilters(
                granularity="fine",
                path_prefix=path  # Custom filter
            )
        )
        fine_results.extend(section_fine)

    # Re-rank combined results
    final_results = sorted(fine_results, key=lambda x: x.score, reverse=True)

    return final_results[:top_paragraphs]
```

---

## 6. Quality Gates & Testing

### 6.1 Unit Tests

#### 6.1.1 Embedding Dimension Validation

```python
"""
Test file: backend/tests/unit/services/test_embeddings.py
"""

import pytest
from app.services.embeddings import EmbeddingService

EXPECTED_DIMENSIONS = 1536

@pytest.mark.asyncio
async def test_embedding_returns_correct_dimensions():
    """Verify embeddings have exactly 1536 dimensions."""
    service = EmbeddingService()
    try:
        embedding = await service.generate_embedding("test text")
        assert len(embedding) == EXPECTED_DIMENSIONS
    finally:
        await service.close()

@pytest.mark.asyncio
async def test_embedding_is_normalized():
    """Verify embeddings are L2 normalized (magnitude ≈ 1.0)."""
    import math

    service = EmbeddingService()
    try:
        embedding = await service.generate_embedding("test text", normalize=True)
        magnitude = math.sqrt(sum(x * x for x in embedding))
        assert abs(magnitude - 1.0) < 0.0001
    finally:
        await service.close()

@pytest.mark.asyncio
async def test_empty_text_raises_error():
    """Verify empty text raises ValueError."""
    service = EmbeddingService()
    try:
        with pytest.raises(ValueError, match="cannot be empty"):
            await service.generate_embedding("")
    finally:
        await service.close()
```

#### 6.1.2 Vector Validation

```python
"""
Test file: backend/tests/unit/services/test_vector_validator.py
"""

import pytest
import math
from app.services.validation.vector_validator import VectorValidator, ValidationResult

def test_valid_vector_passes():
    """Normal vector should pass validation."""
    validator = VectorValidator(expected_dimensions=1536)
    vector = [0.1] * 1536
    result = validator.validate(vector)
    assert result.is_valid

def test_nan_values_fail():
    """Vector with NaN should fail."""
    validator = VectorValidator(expected_dimensions=1536)
    vector = [0.1] * 1535 + [float('nan')]
    result = validator.validate(vector)
    assert not result.is_valid
    assert "NaN" in result.errors[0]

def test_zero_vector_fails():
    """Zero vector should fail."""
    validator = VectorValidator(expected_dimensions=1536)
    vector = [0.0] * 1536
    result = validator.validate(vector)
    assert not result.is_valid
    assert "Zero vector" in result.errors[0]

def test_dimension_mismatch_fails():
    """Wrong dimensions should fail."""
    validator = VectorValidator(expected_dimensions=1536)
    vector = [0.1] * 768  # Wrong size
    result = validator.validate(vector)
    assert not result.is_valid
    assert "Dimension mismatch" in result.errors[0]
```

### 6.2 Integration Tests

```python
"""
Test file: backend/tests/integration/test_embedding_pipeline.py

End-to-end test: chunk → embed → store → retrieve
"""

import pytest
from app.services.chunking.chunker import chunk_document
from app.services.embeddings import EmbeddingService
from app.db.repositories.chunk_repository import ChunkRepository

@pytest.mark.asyncio
async def test_full_pipeline_round_trip(db_session):
    """Test complete embedding pipeline: chunk → embed → store → retrieve."""

    # Sample content
    test_content = """
    # Sleep Hygiene Guide

    Getting quality sleep is essential for overall health.

    ## Tips for Better Sleep

    1. Maintain a consistent sleep schedule
    2. Create a relaxing bedtime routine
    3. Limit screen time before bed
    """

    # 1. Chunk
    coarse, fine = chunk_document(test_content)
    assert len(coarse) > 0
    assert len(fine) > 0

    # 2. Embed
    service = EmbeddingService()
    try:
        embeddings = []
        for chunk in coarse[:2]:  # Limit for test speed
            vector = await service.generate_embedding(chunk.text)
            embeddings.append((chunk, vector))

        assert len(embeddings) == 2
        assert len(embeddings[0][1]) == 1536

        # 3. Store
        repo = ChunkRepository(db_session)
        stored = await repo.create_many([
            {
                "analysis_id": test_analysis_id,
                "granularity": chunk.granularity,
                "path": chunk.path,
                "snippet": chunk.text[:200],
                "vector": vector,
                "hash": chunk.content_hash,
            }
            for chunk, vector in embeddings
        ])

        assert len(stored) == 2

        # 4. Retrieve
        query_embedding = await service.generate_embedding("sleep tips")
        results = await repo.semantic_search(
            query_embedding=query_embedding,
            limit=5
        )

        assert len(results) > 0
        assert results[0][1] > 0.5  # Should have reasonable similarity

    finally:
        await service.close()
```

### 6.3 Smoke Tests (Production Validation)

#### 6.3.1 Metrics & Thresholds

| Metric | Formula | Threshold | Description |
|--------|---------|-----------|-------------|
| **Recall@5** | `relevant_in_top_5 / total_relevant` | ≥ 0.70 | 70% of relevant docs in top 5 |
| **MRR** | `1 / rank_of_first_relevant` | ≥ 0.60 | First relevant doc rank |
| **NDCG@5** | `DCG@5 / IDCG@5` | ≥ 0.65 | Ranking quality |
| **Precision@1** | `relevant_at_position_1` | ≥ 0.50 | Top result relevance |
| **Hit Rate** | `any_relevant_in_top_k` | ≥ 0.80 | At least one hit |

#### 6.3.2 Running Smoke Tests

```bash
# Run all retrieval smoke tests
cd backend
poetry run pytest tests/smoke/retrieval/ -v

# Run with specific markers
poetry run pytest tests/smoke/retrieval/ -v -m "not slow"

# Generate coverage report
poetry run pytest tests/smoke/retrieval/ --cov=app/services/search --cov-report=html
```

#### 6.3.3 Ground Truth Query Format

```json
{
  "queries": [
    {
      "id": "q-sleep-hygiene",
      "query": "tips for better sleep",
      "difficulty": "easy",
      "expected_chunks": ["sleep-guide/tips", "sleep-guide/intro"],
      "min_score": 0.6,
      "description": "Should find sleep tips section"
    },
    {
      "id": "q-nutrition-paraphrase",
      "query": "what foods help with energy levels",
      "difficulty": "medium",
      "expected_chunks": ["nutrition-guide/energy-foods"],
      "min_score": 0.5,
      "description": "Paraphrase test - should match energy/nutrition content"
    }
  ]
}
```

### 6.4 Acceptance Criteria Checklist

Before deploying embeddings to production, verify:

#### Data Quality
- [ ] All PII scrubbed (manual review of 100 random chunks)
- [ ] Content hash uniqueness verified (no duplicates)
- [ ] Token counts within limits (all chunks < 7500 tokens)
- [ ] UTF-8 encoding verified for all content

#### Embedding Quality
- [ ] Dimension validation passed (all vectors = 1536 dims)
- [ ] No NaN or Inf values in vectors
- [ ] L2 normalization verified (magnitude ≈ 1.0)
- [ ] Model version recorded for all embeddings

#### Retrieval Quality
- [ ] Recall@5 ≥ 0.70 on ground truth queries
- [ ] MRR ≥ 0.60 on ground truth queries
- [ ] NDCG@5 ≥ 0.65 on ground truth queries
- [ ] Precision@1 ≥ 0.50 on ground truth queries

#### Performance
- [ ] Embedding latency < 500ms (95th percentile)
- [ ] Search latency < 100ms (95th percentile)
- [ ] HNSW index used (EXPLAIN ANALYZE verification)

#### Storage
- [ ] All chunks stored with required metadata
- [ ] Foreign key constraints satisfied
- [ ] Indexes created and verified

---

## 7. Cost Analysis

### 7.1 Cost Breakdown by Scenario

| Scenario | Documents | Avg Tokens/Doc | Total Tokens | Embedding Cost | Storage Cost/mo | Total One-Time |
|----------|-----------|----------------|--------------|----------------|-----------------|----------------|
| **Pilot** | 100 | 750 | 75K | $0.0015 | $0.01 | ~$0.01 |
| **Small Practice** | 1,000 | 1,500 | 1.5M | $0.03 | $0.10 | ~$0.15 |
| **Medium Clinic** | 10,000 | 2,000 | 20M | $0.40 | $1.00 | ~$1.50 |
| **Large Health System** | 100,000 | 2,500 | 250M | $5.00 | $12.00 | ~$20.00 |

**Pricing basis:**
- OpenAI `text-embedding-3-small`: $0.02 per 1M tokens
- PostgreSQL storage: ~$0.10 per GB/month (1536 floats × 4 bytes = 6KB per embedding)

### 7.2 Cost Estimation Formula

```python
def estimate_embedding_cost(
    document_count: int,
    avg_chars_per_doc: int,
    tokens_per_char: float = 0.25,  # ~4 chars per token for English
    chunks_per_doc: float = 4.0,    # Average chunks after splitting
    price_per_million_tokens: float = 0.02,
) -> dict:
    """
    Estimate embedding costs for a dataset.

    Args:
        document_count: Number of documents to embed
        avg_chars_per_doc: Average characters per document
        tokens_per_char: Token-to-character ratio (default 0.25)
        chunks_per_doc: Average chunks per document after splitting
        price_per_million_tokens: OpenAI pricing ($0.02/1M for 3-small)

    Returns:
        Cost breakdown dictionary
    """
    # Estimate tokens
    tokens_per_doc = avg_chars_per_doc * tokens_per_char
    total_tokens = document_count * tokens_per_doc * chunks_per_doc

    # Calculate costs
    embedding_cost = (total_tokens / 1_000_000) * price_per_million_tokens

    # Storage estimate (6KB per vector, $0.10/GB/month)
    total_chunks = document_count * chunks_per_doc
    storage_gb = (total_chunks * 6 * 1024) / (1024 ** 3)
    storage_cost_monthly = storage_gb * 0.10

    return {
        "document_count": document_count,
        "estimated_tokens": int(total_tokens),
        "estimated_chunks": int(total_chunks),
        "embedding_cost_usd": round(embedding_cost, 4),
        "storage_cost_monthly_usd": round(storage_cost_monthly, 4),
        "total_one_time_usd": round(embedding_cost + storage_cost_monthly, 4),
    }

# Example usage
cost = estimate_embedding_cost(
    document_count=1000,
    avg_chars_per_doc=6000,  # ~1500 tokens
)
print(cost)
# {'document_count': 1000, 'estimated_tokens': 6000000, 'estimated_chunks': 4000,
#  'embedding_cost_usd': 0.12, 'storage_cost_monthly_usd': 0.0234, 'total_one_time_usd': 0.1434}
```

### 7.3 Cost Optimization Strategies

| Strategy | Savings | Implementation |
|----------|---------|----------------|
| **Content deduplication** | 20-40% | Hash-based check before embedding |
| **Batch API calls** | 0% direct, faster | Use `generate_embeddings_batch()` |
| **Skip short docs** | 10-20% | Don't chunk docs < 500 tokens |
| **Incremental updates** | 50-80% | Only embed new/changed content |
| **Model selection** | Variable | Use 3-small for most cases |

---

## 8. Extension Points

### 8.1 Custom Chunking Strategies

#### 8.1.1 SOAP Note Chunking (Medical)

```python
"""
Custom chunker for SOAP (Subjective, Objective, Assessment, Plan) notes.
"""

import re
from dataclasses import dataclass

@dataclass
class SOAPChunk:
    """A chunk from a SOAP note."""
    section: str  # S, O, A, or P
    text: str
    chunk_idx: int
    chunk_total: int = 4


def chunk_soap_note(text: str) -> list[SOAPChunk]:
    """
    Split a SOAP note into its four sections.

    Expected format:
    S: Patient reports...
    O: Vitals: BP 120/80...
    A: Assessment of condition...
    P: Plan includes...
    """
    sections = {
        "S": "Subjective",
        "O": "Objective",
        "A": "Assessment",
        "P": "Plan"
    }

    chunks = []
    pattern = r'^([SOAP]):\s*(.+?)(?=^[SOAP]:|$)'

    matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)

    for idx, (section_code, content) in enumerate(matches):
        chunks.append(SOAPChunk(
            section=sections.get(section_code, section_code),
            text=content.strip(),
            chunk_idx=idx,
            chunk_total=len(matches)
        ))

    return chunks
```

#### 8.1.2 Q&A Pair Chunking

```python
"""
Custom chunker for Q&A pairs - keeps question and answer together.
"""

@dataclass
class QAPairChunk:
    """A question-answer pair as a single chunk."""
    question: str
    answer: str
    chunk_idx: int
    chunk_total: int


def chunk_qa_pairs(qa_list: list[dict]) -> list[QAPairChunk]:
    """
    Convert Q&A pairs into chunks.

    Input format: [{"question": "...", "answer": "..."}, ...]
    """
    chunks = []

    for idx, qa in enumerate(qa_list):
        # Combine Q&A with clear delimiter
        combined_text = f"Question: {qa['question']}\n\nAnswer: {qa['answer']}"

        chunks.append(QAPairChunk(
            question=qa['question'],
            answer=qa['answer'],
            chunk_idx=idx,
            chunk_total=len(qa_list)
        ))

    return chunks
```

### 8.2 Alternative Embedding Models

| Model | Dimensions | Cost/1M tokens | Strengths | Weaknesses |
|-------|------------|----------------|-----------|------------|
| `text-embedding-3-small` | 1536 | $0.02 | Balance of cost/quality | Moderate accuracy |
| `text-embedding-3-large` | 3072 | $0.13 | Highest accuracy | 6.5x cost, needs schema change |
| `text-embedding-ada-002` | 1536 | $0.10 | Legacy compatibility | Deprecated, 5x cost |
| `nomic-embed-text` | 768 | $0 (local) | Free, no API calls | Lower quality, needs infra |
| `voyage-large-2` | 1024 | $0.12 | Strong on code | Different dimensions |

**Migration note:** Changing models requires:
1. Schema migration if dimensions change
2. Re-embedding all content (hash includes model version)
3. Index rebuild

### 8.3 Model Migration Script

```python
"""
Script to migrate embeddings to a new model.

Location: backend/scripts/migrate_embedding_model.py
"""

import asyncio
from app.services.embeddings import EmbeddingService
from app.db.repositories.chunk_repository import ChunkRepository

async def migrate_embeddings(
    old_model: str,
    new_model: str,
    batch_size: int = 100,
):
    """
    Re-embed all chunks with a new model.

    WARNING: This is a potentially expensive operation.
    """
    # Query all chunks with old model
    async with async_session_maker() as session:
        repo = ChunkRepository(session)

        # Get chunks needing migration
        chunks = await repo.get_chunks_by_model(old_model)
        print(f"Found {len(chunks)} chunks to migrate")

        # Initialize new embedding service
        service = EmbeddingService()  # Uses new model from config

        try:
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]

                # Get texts from snippets
                texts = [c.snippet for c in batch]

                # Generate new embeddings
                results = await service.generate_embeddings_batch(
                    texts=texts,
                    normalize=True
                )

                # Update chunks with new embeddings
                for chunk, (vector, _) in zip(batch, results):
                    chunk.vector = vector
                    chunk.model = new_model
                    chunk.model_version = "v1"

                await session.commit()
                print(f"Migrated {min(i + batch_size, len(chunks))}/{len(chunks)}")

        finally:
            await service.close()

    print("Migration complete!")
```

---

## 9. Troubleshooting & FAQs

### 9.1 Common Issues

#### Issue: "429 Too Many Requests" from OpenAI

**Symptoms:** Embedding requests failing with rate limit errors.

**Solutions:**
1. Reduce batch size: `BATCH_SIZE_MAX=50` in `.env`
2. Add manual delay between batches
3. Upgrade OpenAI API tier for higher limits
4. The service has built-in backpressure - it will auto-adjust

```python
# Manual rate limiting if needed
import asyncio

for batch in batches:
    await embed_batch(batch)
    await asyncio.sleep(1)  # 1 second delay between batches
```

#### Issue: Database query slow (>5 seconds)

**Symptoms:** Semantic search taking too long.

**Solutions:**
1. Verify HNSW index is being used:
```sql
EXPLAIN ANALYZE
SELECT * FROM analysis_chunks
ORDER BY vector <=> '[...]'::vector
LIMIT 10;
-- Should show: Index Scan using ix_analysis_chunks_vector_hnsw
```

2. If not using index, rebuild:
```sql
REINDEX INDEX ix_analysis_chunks_vector_hnsw;
```

3. Increase `ef_search` for accuracy vs speed tradeoff:
```sql
SET hnsw.ef_search = 100;  -- Higher = more accurate, slower
```

#### Issue: PII detected in embedded chunks

**Symptoms:** Manual review finds PII that wasn't caught.

**Solutions:**
1. Update regex patterns for missed patterns
2. Add custom patterns for domain-specific PII
3. Use stricter NER model (e.g., `en_core_web_lg`)
4. Implement mandatory manual review for health data

```python
# Add custom pattern
CUSTOM_PATTERNS = {
    "member_id": r"MEM\d{10}",
    "patient_id": r"PT-\d{6}",
}
```

#### Issue: Low recall on semantic search

**Symptoms:** Relevant documents not appearing in top results.

**Solutions:**
1. Try hybrid search instead of pure semantic
2. Check if content was properly chunked (not too large)
3. Verify embeddings are normalized
4. Consider if query needs reformulation

### 9.2 FAQs

**Q: Can I embed non-English content?**

A: Yes, `text-embedding-3-small` supports 100+ languages. Performance may vary by language - test with ground truth queries in your target language.

**Q: How do I handle very long transcripts (50K+ tokens)?**

A: Use time-based windowing:
```python
# Split by time segments (e.g., 10-minute windows)
def chunk_long_transcript(transcript, window_minutes=10):
    segments = split_by_time(transcript, window_minutes)
    return [chunk_segment(seg) for seg in segments]
```

**Q: What's the difference between coarse and fine chunks?**

A:
- **Coarse**: Section/paragraph level. Good for finding relevant topics.
- **Fine**: Sentence/phrase level with overlap. Good for precise answers.
- Use coarse-to-fine retrieval: find sections first, then drill down.

**Q: How often should I re-embed content?**

A:
- Model change: Must re-embed everything
- Content update: Re-embed only changed documents (hash-based detection)
- Routine: No need to re-embed if content unchanged

**Q: Can I use embeddings for clustering/classification?**

A: Yes, the 1536-dimensional vectors work well for:
- K-means clustering (topic grouping)
- Classification (train on labeled examples)
- Anomaly detection (distance from centroid)

---

## 10. Appendices

### Appendix A: Complete Schema Reference

```sql
-- Full DDL for analysis_chunks table
-- See Section 5.4.1 for complete schema

-- Additional useful queries

-- Count chunks by granularity
SELECT granularity, COUNT(*)
FROM analysis_chunks
GROUP BY granularity;

-- Find duplicate hashes
SELECT hash, COUNT(*) as count
FROM analysis_chunks
GROUP BY hash
HAVING COUNT(*) > 1;

-- Check vector statistics
SELECT
    COUNT(*) as total_chunks,
    AVG(token_count) as avg_tokens,
    SUM(CASE WHEN was_truncated THEN 1 ELSE 0 END) as truncated_count
FROM analysis_chunks;

-- Verify index usage
SELECT
    indexrelname as index_name,
    idx_scan as scans,
    idx_tup_read as tuples_read
FROM pg_stat_user_indexes
WHERE relname = 'analysis_chunks';
```

### Appendix B: Glossary

| Term | Definition |
|------|------------|
| **Embedding** | Dense vector representation of text, capturing semantic meaning |
| **Chunking** | Splitting documents into smaller pieces for embedding |
| **Coarse chunk** | Large chunk (section/paragraph level) |
| **Fine chunk** | Small chunk (sentence level with overlap) |
| **HNSW** | Hierarchical Navigable Small World - fast approximate nearest neighbor algorithm |
| **RRF** | Reciprocal Rank Fusion - method to combine multiple ranked lists |
| **L2 Normalization** | Scaling vector to unit length for cosine similarity |
| **pgvector** | PostgreSQL extension for vector similarity search |
| **kNN** | k-Nearest Neighbors - finding k most similar vectors |
| **tsvector** | PostgreSQL full-text search vector representation |
| **MRR** | Mean Reciprocal Rank - evaluation metric |
| **NDCG** | Normalized Discounted Cumulative Gain - ranking quality metric |
| **PII** | Personally Identifiable Information |
| **PHI** | Protected Health Information (HIPAA) |

### Appendix C: Related Documentation

- [Architecture Overview](./ARCHITECTURE.md)
- [Configuration Guide](./CONFIGURATION.md)
- [Issue #215: Embedding Pipeline Hardening](./issues/215-embedding-pipeline-hardening/)
- [Issue #221: Search Service](./issues/221-search-service/)
- [Issue #223: Retrieval Smoke Tests](./issues/223-retrieval-smoke-tests/)
- [Embedding Cost Analysis](./EMBEDDING_COST_ANALYSIS.md)

### Appendix D: AI Agent Compatibility Metadata

```yaml
# Machine-parseable metadata for AI agent evaluation
# Use this section for automated data compatibility assessment

ai_agent_checklist:
  version: "1.0.0"

  required_fields:
    - content_id
    - text
    - content_type

  optional_fields:
    - metadata.title
    - metadata.author
    - metadata.created_at
    - metadata.language
    - metadata.tags
    - metadata.source
    - metadata.has_pii

  content_type_enum:
    - article
    - transcript
    - qa_pair
    - research_paper
    - medical_note
    - other

  compatibility_scoring:
    excellent:
      criteria:
        - "text_based: true"
        - "structured: true"
        - "pii_free: true"
        - "token_range: 200-7500"
      score_range: "0.9-1.0"
      recommendation: "PROCEED"

    good:
      criteria:
        - "text_based: true"
        - "conversational: true"
        - "pii_scrubbed: true"
        - "token_range: 100-10000"
      score_range: "0.7-0.89"
      recommendation: "PROCEED_WITH_REVIEW"

    marginal:
      criteria:
        - "text_based: true"
        - "unstructured: true"
        - "pii_detected: true"
      score_range: "0.5-0.69"
      recommendation: "MANUAL_REVIEW_REQUIRED"

    poor:
      criteria:
        - "binary_data: true"
        - "pii_heavy: true"
        - "token_count: >100000"
      score_range: "0.0-0.49"
      recommendation: "NOT_SUITABLE"

  validation_scripts:
    token_estimation: "Section 7.2"
    pii_detection: "Section 3.4"
    schema_validation: "Section 3.3"
    quality_gates: "Section 6.4"

  evaluation_workflow:
    step_1: "Parse Quick Start Checklist (Section 2)"
    step_2: "Validate JSON schema (Section 3.3)"
    step_3: "Run PII detection (Section 3.4)"
    step_4: "Estimate costs (Section 7.2)"
    step_5: "Generate compatibility report"

  output_format:
    type: "json"
    fields:
      - evaluation_id
      - dataset_name
      - phase_1_data_compatibility
      - phase_2_privacy
      - phase_3_quality
      - compatibility_score
      - overall_recommendation
      - notes

# Example AI agent evaluation output
example_output:
  evaluation_id: "eval-2025-12-13-001"
  dataset_name: "health_coaching_v1"
  phase_1_data_compatibility:
    text_based: true
    utf8_encoded: true
    token_range_valid: true
    structured_format: "json"
    has_content_ids: true
    pass: true
  phase_2_privacy:
    pii_scan_complete: true
    pii_removed: true
    health_data_reviewed: true
    pass: true
  phase_3_quality:
    ground_truth_query_count: 50
    content_types: ["article", "transcript"]
    duplicate_count: 0
    pass: true
  compatibility_score: 0.95
  overall_recommendation: "PROCEED"
  notes: "Dataset meets all requirements. Ready for embedding."
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-13 | SkillForge Team | Initial release |

---

**End of Document**
