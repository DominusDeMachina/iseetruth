# Story 3.4: Vector Embedding Generation & Storage

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an investigator,
I want my document content to be semantically searchable,
So that natural language queries can find relevant passages even when exact keywords don't match.

## Acceptance Criteria

1. GIVEN document chunks exist, WHEN the processing pipeline reaches the embedding stage, THEN vector embeddings are generated for each chunk using Ollama `qwen3-embedding:8b`, AND embeddings are stored in the single Qdrant collection `document_chunks` with `investigation_id` as a payload filter field, AND each embedding point links to its source chunk via `chunk_id` in the payload, AND the document status transitions through `"embedding"` → `"complete"`.

2. GIVEN the full pipeline runs on a 100-page PDF, WHEN processing completes (text extraction + entity extraction + embedding), THEN total processing time is <15 minutes on minimum hardware (16GB RAM, 8GB VRAM). *(NFR — not directly testable in unit tests; tracked as a performance benchmark.)*

3. GIVEN embedding generation fails for a chunk, WHEN Ollama returns an error, THEN the failure is logged with `chunk_id` and `document_id`, AND the remaining chunks are still processed (per-chunk failure does not abort the batch), AND already-stored entities and relationships from Stage 3 remain intact (no rollback), AND the document is still marked `"complete"` at the end (partial embedding is acceptable for the MVP).

## Tasks / Subtasks

- [x] **Task 1: Create `app/llm/embeddings.py`** — Ollama embedding client (AC: 1, 3)
  - [x] 1.1: Define `EMBEDDING_MODEL = "qwen3-embedding:8b"` constant
  - [x] 1.2: Implement `OllamaEmbeddingClient` class with `__init__(self, base_url: str)`
  - [x] 1.3: Implement `embed(self, text: str) -> list[float]` — POST to `/api/embed`, return `data["embeddings"][0]`
  - [x] 1.4: Use same `INFERENCE_TIMEOUT` pattern as `app/llm/client.py` (import from there or redefine)
  - [x] 1.5: Raise `OllamaUnavailableError` on `httpx.ConnectError`, `httpx.TimeoutException`, `httpx.HTTPStatusError`
  - [x] 1.6: Log at DEBUG level: `"Embedding generated"`, `model=EMBEDDING_MODEL`, `dimension=len(vector)`

- [x] **Task 2: Update `app/db/qdrant.py`** — add collection constants and `ensure_qdrant_collection` (AC: 1)
  - [x] 2.1: Add `COLLECTION_NAME = "document_chunks"` constant
  - [x] 2.2: Add `VECTOR_SIZE = 4096` constant (qwen3-embedding:8b default output dimension)
  - [x] 2.3: Import `Distance, VectorParams` from `qdrant_client.models`
  - [x] 2.4: Implement `ensure_qdrant_collection(qdrant_client: QdrantClient) -> None` — idempotent: get existing collection names, create only if `COLLECTION_NAME` is absent
  - [x] 2.5: Log `"Created Qdrant collection"` on creation, `"Qdrant collection already exists"` on skip

- [x] **Task 3: Create `app/services/embedding.py`** — EmbeddingService (AC: 1, 3)
  - [x] 3.1: Import `PointStruct` from `qdrant_client.models`; `COLLECTION_NAME` from `app.db.qdrant`
  - [x] 3.2: Define `@dataclass EmbeddingSummary` with fields: `embedded_count: int`, `failed_count: int`, `chunk_count: int`
  - [x] 3.3: Implement `EmbeddingService` class with `__init__(self, embedding_client: OllamaEmbeddingClient, qdrant_client: QdrantClient)`
  - [x] 3.4: Implement `embed_chunks(self, chunks: list, investigation_id: uuid.UUID) -> EmbeddingSummary` — iterate chunks, embed, upsert to Qdrant
  - [x] 3.5: Qdrant point ID = `str(chunk.id)` (UUID string is valid as Qdrant point ID)
  - [x] 3.6: Qdrant point payload fields: `chunk_id` (str), `document_id` (str), `investigation_id` (str), `page_start` (int), `page_end` (int), `text_excerpt` (first 500 chars of `chunk.text`)
  - [x] 3.7: Per-chunk exception: log error with `chunk_id`, `document_id`, `error`; increment `failed_count`; continue to next chunk (do NOT re-raise)
  - [x] 3.8: Return `EmbeddingSummary` with final counts

- [x] **Task 4: Update `app/worker/tasks/process_document.py`** — add Stage 4 (AC: 1, 3)
  - [x] 4.1: Import `OllamaEmbeddingClient` from `app.llm.embeddings`
  - [x] 4.2: Import `EmbeddingService` from `app.services.embedding`
  - [x] 4.3: Import `client as qdrant_client` from `app.db.qdrant`
  - [x] 4.4: After entity extraction success, add Stage 4 block: set `document.status = "embedding"`, commit, publish `"document.processing"` event with `stage="embedding"`
  - [x] 4.5: Instantiate `OllamaEmbeddingClient(settings.ollama_base_url)` and `EmbeddingService(embedding_client, qdrant_client)`
  - [x] 4.6: Call `embedding_service.embed_chunks(chunks, investigation_id=document.investigation_id)`
  - [x] 4.7: If `emb_summary.failed_count > 0`, log WARNING with `failed_count` and `embedded_count`; otherwise log INFO `"Embedding generation complete"`
  - [x] 4.8: After embedding (success or partial), set `document.status = "complete"` and commit (remove the old "All stages complete" block that was at the end of entity extraction)
  - [x] 4.9: Publish `"document.complete"` event with `entity_count`, `relationship_count`, and `embedded_count`

- [x] **Task 5: Update `app/main.py`** — call `ensure_qdrant_collection` at startup (AC: 1)
  - [x] 5.1: Import `client as qdrant_client_sync` from `app.db.qdrant` and `ensure_qdrant_collection` from `app.db.qdrant`
  - [x] 5.2: In `lifespan()`, after `ensure_neo4j_constraints` call, add: `await asyncio.to_thread(ensure_qdrant_collection, qdrant_client_sync)` with surrounding log statements

- [x] **Task 6: Write tests `tests/services/test_embedding.py`** (AC: 1, 3)
  - [x] 6.1: `test_embed_chunks_generates_and_upserts` — mock `OllamaEmbeddingClient.embed` returning `[0.1]*4096`; verify `qdrant_client.upsert` called once per chunk with correct `collection_name`, `id=str(chunk.id)`, and payload fields
  - [x] 6.2: `test_embed_chunks_returns_summary` — verify `EmbeddingSummary` counts match chunk count
  - [x] 6.3: `test_embed_chunks_per_chunk_failure_continues` — mock `embed` to raise `OllamaUnavailableError` on chunk 1 but succeed on chunk 2; verify `failed_count=1`, `embedded_count=1`, and `qdrant_client.upsert` called once
  - [x] 6.4: `test_embed_chunks_empty_list` — verify no calls to `embed` or `upsert` when `chunks=[]`
  - [x] 6.5: `test_payload_contains_investigation_id` — verify `payload["investigation_id"] == str(investigation_id)`
  - [x] 6.6: `test_text_excerpt_truncated_to_500` — chunk with text > 500 chars; verify `payload["text_excerpt"]` is exactly 500 chars

## Dev Notes

### Architecture Context

This story completes the **document processing pipeline** (Story 3.1 → 3.2 → 3.3 → 3.4):
```
Stage 1: extracting_text  → TextExtractionService (PyMuPDF)
Stage 2: chunking         → ChunkingService
Stage 3: extracting_entities → EntityExtractionService (Ollama qwen3.5:9b → Neo4j)
Stage 4: embedding        → EmbeddingService (Ollama qwen3-embedding:8b → Qdrant)  ← THIS STORY
→ complete
```

**After this story**, the Qdrant `document_chunks` collection will be populated and ready for the GRAPH FIRST Q&A pipeline (Epic 5).

### Qdrant Data Model

**Collection:** `document_chunks` (single global collection — architecture decision, not per-investigation)
**Vector size:** 4096 (qwen3-embedding:8b default)
**Distance:** Cosine

**Point structure:**
```
id:     str(chunk.id)  — UUID string, 1:1 with DocumentChunk.id in PostgreSQL
vector: list[float]    — 4096-dimensional embedding
payload: {
  "chunk_id":        str  — same as point ID, for explicit payload-level lookup
  "document_id":     str  — FK to PostgreSQL documents.id
  "investigation_id": str — filter key for all queries; mandatory for deletion cascade
  "page_start":      int
  "page_end":        int
  "text_excerpt":    str  — first 500 chars of chunk.text (inline, avoids cross-DB join)
}
```

**Investigation deletion (future — Epic story on cascading delete):**
Delete by payload filter: `filter=Filter(must=[FieldCondition(key="investigation_id", match=MatchValue(value=str(investigation_id)))])`
This is why `investigation_id` MUST be in the payload.

### `app/llm/embeddings.py` Implementation Guide

Use Ollama `/api/embed` endpoint (not the older `/api/embeddings`):

```python
# POST /api/embed
body = {"model": "qwen3-embedding:8b", "input": text}
response_json = {"embeddings": [[0.1, 0.2, ...]]}  # list of vectors

# Extract single vector:
vector = response_json["embeddings"][0]
```

Use the same `INFERENCE_TIMEOUT` from `app/llm/client.py` — re-import it rather than redefining:

```python
from app.llm.client import INFERENCE_TIMEOUT  # httpx.Timeout(connect=5.0, read=None, write=10.0, pool=5.0)
```

Full implementation shape:
```python
import httpx
from loguru import logger
from app.exceptions import OllamaUnavailableError
from app.llm.client import INFERENCE_TIMEOUT

EMBEDDING_MODEL = "qwen3-embedding:8b"

class OllamaEmbeddingClient:
    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip("/")

    def embed(self, text: str) -> list[float]:
        body = {"model": EMBEDDING_MODEL, "input": text}
        try:
            with httpx.Client(timeout=INFERENCE_TIMEOUT) as http:
                response = http.post(f"{self._base_url}/api/embed", json=body)
                response.raise_for_status()
                data = response.json()
                vector = data["embeddings"][0]
                logger.debug("Embedding generated", model=EMBEDDING_MODEL, dimension=len(vector))
                return vector
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            logger.error("Ollama unavailable for embedding", error=str(exc))
            raise OllamaUnavailableError(f"Ollama unavailable for embedding: {exc}") from exc
```

### `app/db/qdrant.py` — ensure_qdrant_collection

Import pattern and implementation:
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from app.config import get_settings
from loguru import logger

settings = get_settings()
client = QdrantClient(url=settings.qdrant_url)

COLLECTION_NAME = "document_chunks"
VECTOR_SIZE = 4096  # qwen3-embedding:8b default output dimensions


def ensure_qdrant_collection(qdrant_client: QdrantClient) -> None:
    """Create Qdrant collection if it doesn't exist. Idempotent — safe to call on every deploy."""
    existing_names = {c.name for c in qdrant_client.get_collections().collections}
    if COLLECTION_NAME not in existing_names:
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection", collection=COLLECTION_NAME)
    else:
        logger.debug("Qdrant collection already exists", collection=COLLECTION_NAME)
```

### `app/services/embedding.py` — EmbeddingService

```python
import uuid
from dataclasses import dataclass

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from app.db.qdrant import COLLECTION_NAME
from app.llm.embeddings import OllamaEmbeddingClient


@dataclass
class EmbeddingSummary:
    embedded_count: int
    failed_count: int
    chunk_count: int


class EmbeddingService:
    def __init__(self, embedding_client: OllamaEmbeddingClient, qdrant_client: QdrantClient):
        self.embedding_client = embedding_client
        self.qdrant_client = qdrant_client

    def embed_chunks(
        self,
        chunks: list,
        investigation_id: uuid.UUID,
    ) -> EmbeddingSummary:
        """Generate embeddings for all chunks and store in Qdrant.

        Per-chunk failures are logged and skipped — they do NOT abort the batch.
        Returns summary with counts for caller to decide on logging/alerting.
        """
        embedded_count = 0
        failed_count = 0

        for chunk in chunks:
            try:
                vector = self.embedding_client.embed(chunk.text)
                self.qdrant_client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=[
                        PointStruct(
                            id=str(chunk.id),
                            vector=vector,
                            payload={
                                "chunk_id": str(chunk.id),
                                "document_id": str(chunk.document_id),
                                "investigation_id": str(investigation_id),
                                "page_start": chunk.page_start,
                                "page_end": chunk.page_end,
                                "text_excerpt": chunk.text[:500],
                            },
                        )
                    ],
                )
                embedded_count += 1
            except Exception as exc:
                logger.error(
                    "Embedding failed for chunk",
                    chunk_id=str(chunk.id),
                    document_id=str(chunk.document_id),
                    error=str(exc),
                )
                failed_count += 1

        return EmbeddingSummary(
            embedded_count=embedded_count,
            failed_count=failed_count,
            chunk_count=len(chunks),
        )
```

### `process_document.py` — Stage 4 addition

Add imports at the top of the file:
```python
from app.db.qdrant import client as qdrant_sync_client
from app.llm.embeddings import OllamaEmbeddingClient
from app.services.embedding import EmbeddingService
```

Replace the current "All stages complete" block (the final `document.status = "complete"` section) with:
```python
# Stage 4: Embedding generation
document.status = "embedding"
session.commit()

_publish_safe(
    "document.processing",
    {
        "document_id": document_id,
        "stage": "embedding",
        "chunk_count": len(chunks),
        "progress": 0.0,
    },
)

embedding_client = OllamaEmbeddingClient(settings.ollama_base_url)
embedding_service = EmbeddingService(embedding_client, qdrant_sync_client)
emb_summary = embedding_service.embed_chunks(
    chunks, investigation_id=document.investigation_id
)

if emb_summary.failed_count > 0:
    logger.warning(
        "Some chunks failed embedding — partial embeddings stored",
        document_id=document_id,
        embedded_count=emb_summary.embedded_count,
        failed_count=emb_summary.failed_count,
    )
else:
    logger.info(
        "Embedding generation complete",
        document_id=document_id,
        embedded_count=emb_summary.embedded_count,
    )

# All stages complete
document.status = "complete"
session.commit()

logger.info(
    "Document processing complete",
    document_id=document_id,
    investigation_id=investigation_id,
    entity_count=summary.entity_count,
    relationship_count=summary.relationship_count,
    embedded_count=emb_summary.embedded_count,
)

_publish_safe(
    "document.complete",
    {
        "document_id": document_id,
        "entity_count": summary.entity_count,
        "relationship_count": summary.relationship_count,
        "embedded_count": emb_summary.embedded_count,
    },
)
```

**Important:** `summary` is still in scope from Stage 3 (entity extraction). `emb_summary` is new. Both must be in scope when publishing `document.complete`.

### `app/main.py` — lifespan update

```python
# Add imports
from app.db.qdrant import client as qdrant_client_sync, ensure_qdrant_collection

# In lifespan(), after Neo4j constraints:
logger.info("Setting up Qdrant collection")
await asyncio.to_thread(ensure_qdrant_collection, qdrant_client_sync)
logger.info("Qdrant collection setup complete")
```

### Testing Guide (`tests/services/test_embedding.py`)

Use `unittest.mock.MagicMock` for both `OllamaEmbeddingClient` and `QdrantClient`. No async mocking needed — all operations in `EmbeddingService` are synchronous.

```python
import uuid
from unittest.mock import MagicMock, call
import pytest
from app.services.embedding import EmbeddingService, EmbeddingSummary
from app.exceptions import OllamaUnavailableError


@pytest.fixture
def mock_embedding_client():
    client = MagicMock()
    client.embed.return_value = [0.1] * 4096
    return client


@pytest.fixture
def mock_qdrant_client():
    return MagicMock()


@pytest.fixture
def make_chunk():
    def _make(text="Test chunk text", page_start=1, page_end=1):
        chunk = MagicMock()
        chunk.id = uuid.uuid4()
        chunk.document_id = uuid.uuid4()
        chunk.text = text
        chunk.page_start = page_start
        chunk.page_end = page_end
        return chunk
    return _make


def test_embed_chunks_generates_and_upserts(mock_embedding_client, mock_qdrant_client, make_chunk):
    investigation_id = uuid.uuid4()
    chunk = make_chunk()
    service = EmbeddingService(mock_embedding_client, mock_qdrant_client)

    summary = service.embed_chunks([chunk], investigation_id)

    mock_embedding_client.embed.assert_called_once_with(chunk.text)
    mock_qdrant_client.upsert.assert_called_once()
    call_kwargs = mock_qdrant_client.upsert.call_args
    point = call_kwargs.kwargs["points"][0]
    assert point.id == str(chunk.id)
    assert point.vector == [0.1] * 4096
    assert point.payload["investigation_id"] == str(investigation_id)
    assert point.payload["chunk_id"] == str(chunk.id)
    assert point.payload["document_id"] == str(chunk.document_id)


def test_embed_chunks_returns_summary(mock_embedding_client, mock_qdrant_client, make_chunk):
    chunks = [make_chunk(), make_chunk()]
    service = EmbeddingService(mock_embedding_client, mock_qdrant_client)
    summary = service.embed_chunks(chunks, uuid.uuid4())
    assert summary.embedded_count == 2
    assert summary.failed_count == 0
    assert summary.chunk_count == 2


def test_embed_chunks_per_chunk_failure_continues(mock_embedding_client, mock_qdrant_client, make_chunk):
    chunk1, chunk2 = make_chunk(), make_chunk()
    mock_embedding_client.embed.side_effect = [
        OllamaUnavailableError("timeout"), [0.1] * 4096
    ]
    service = EmbeddingService(mock_embedding_client, mock_qdrant_client)
    summary = service.embed_chunks([chunk1, chunk2], uuid.uuid4())
    assert summary.failed_count == 1
    assert summary.embedded_count == 1
    mock_qdrant_client.upsert.assert_called_once()


def test_embed_chunks_empty_list(mock_embedding_client, mock_qdrant_client):
    service = EmbeddingService(mock_embedding_client, mock_qdrant_client)
    summary = service.embed_chunks([], uuid.uuid4())
    assert summary.chunk_count == 0
    assert summary.embedded_count == 0
    mock_embedding_client.embed.assert_not_called()
    mock_qdrant_client.upsert.assert_not_called()


def test_payload_contains_investigation_id(mock_embedding_client, mock_qdrant_client, make_chunk):
    investigation_id = uuid.uuid4()
    chunk = make_chunk()
    service = EmbeddingService(mock_embedding_client, mock_qdrant_client)
    service.embed_chunks([chunk], investigation_id)
    point = mock_qdrant_client.upsert.call_args.kwargs["points"][0]
    assert point.payload["investigation_id"] == str(investigation_id)


def test_text_excerpt_truncated_to_500(mock_embedding_client, mock_qdrant_client, make_chunk):
    long_text = "x" * 700
    chunk = make_chunk(text=long_text)
    service = EmbeddingService(mock_embedding_client, mock_qdrant_client)
    service.embed_chunks([chunk], uuid.uuid4())
    point = mock_qdrant_client.upsert.call_args.kwargs["points"][0]
    assert len(point.payload["text_excerpt"]) == 500
```

### Project Structure Notes

**New files:**
- `apps/api/app/llm/embeddings.py` — `OllamaEmbeddingClient` for Ollama `/api/embed`
- `apps/api/app/services/embedding.py` — `EmbeddingService` (sync; used in Celery context)
- `apps/api/tests/services/test_embedding.py` — unit tests for EmbeddingService

**Modified files:**
- `apps/api/app/db/qdrant.py` — add `COLLECTION_NAME`, `VECTOR_SIZE`, `ensure_qdrant_collection()`
- `apps/api/app/worker/tasks/process_document.py` — add Stage 4 ("embedding") before "complete"; pass `embedded_count` in `document.complete` event
- `apps/api/app/main.py` — call `ensure_qdrant_collection` in lifespan startup

**No Alembic migration needed:** `document.status` is a plain `String(20)` field — `"embedding"` (9 chars) fits without schema change.

**No new Python packages needed:** `qdrant-client` already in use (`app/db/qdrant.py`); `httpx` already in use (`app/llm/client.py`).

**Architecture alignment:**
- Qdrant collection name: snake_case (`document_chunks`) ✓ per naming conventions
- Single global collection with `investigation_id` payload filter ✓ per architecture decision
- Embedding through `app/llm/embeddings.py` (not directly in services) ✓ per architecture: "services never call Ollama directly"
- `ensure_qdrant_collection` called at startup (like `ensure_neo4j_constraints`) ✓ idempotent pattern

**Qdrant architecture decision NOTE:**
Architecture doc marks Qdrant collection configuration (vector dimensions, distance, HNSW params) as "deferred to deployment tuning" (depends on qwen3-embedding:8b specifics). The 4096 dimension and Cosine distance are the correct defaults for qwen3-embedding:8b — implement these and document in code. No HNSW tuning is needed for MVP.

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 3, Story 3.4 user story and acceptance criteria]
- [Source: _bmad-output/planning-artifacts/architecture.md — Qdrant single collection decision: `document_chunks`, `investigation_id` payload filter, filtered delete for investigation cascade]
- [Source: _bmad-output/planning-artifacts/architecture.md — LLM models: qwen3-embedding:8b for embeddings; Ollama for all LLM calls]
- [Source: _bmad-output/planning-artifacts/architecture.md — File structure: `app/llm/embeddings.py`, `app/services/embedding.py`, `app/db/qdrant.py`, `tests/services/test_embedding.py`]
- [Source: _bmad-output/planning-artifacts/architecture.md — Naming: Qdrant collection = snake_case `document_chunks`]
- [Source: apps/api/app/db/qdrant.py — existing QdrantClient instantiation pattern; `settings.qdrant_url`]
- [Source: apps/api/app/llm/client.py — INFERENCE_TIMEOUT constant; OllamaClient httpx pattern; OllamaUnavailableError usage]
- [Source: apps/api/app/services/extraction.py — EmbeddingService class shape mirrors EntityExtractionService: class-based, __init__ takes dependencies]
- [Source: apps/api/app/worker/tasks/process_document.py — Stage pattern: set status, commit, publish event, call service, handle errors, log; `summary` var from Stage 3 stays in scope]
- [Source: apps/api/app/main.py — lifespan startup pattern: `await asyncio.to_thread(ensure_neo4j_constraints, sync_neo4j_driver)` → mirror for Qdrant]
- [Source: apps/api/app/config.py — `settings.ollama_base_url` for Ollama URL]
- [Source: apps/api/app/exceptions.py — OllamaUnavailableError for connection failures]

### Previous Story Intelligence (Story 3.3 Learnings)

1. **Class-based services with injected dependencies** — `EmbeddingService(embedding_client, qdrant_client)` mirrors `EntityExtractionService(ollama_client, neo4j_driver)` and `EntityQueryService(neo4j_driver, db)`. All dependencies injected; no global state in services.

2. **Celery uses sync drivers** — `process_document.py` uses `sync_neo4j_driver` (not the async driver from `app/db/neo4j.py`). Similarly for Qdrant: use the sync `QdrantClient` from `app/db/qdrant.py` (it is already sync — no sync/async variant needed for Qdrant).

3. **Startup initialization pattern** — `ensure_neo4j_constraints` is called in `lifespan()` via `asyncio.to_thread` (since it's a sync function called from async context). Do the same for `ensure_qdrant_collection`.

4. **Per-chunk error handling** — Story 3.3 established that Neo4j write failures propagate up and mark the document "failed". For embedding (Story 3.4), the spec explicitly says per-chunk failures should be logged and skipped (not document-level failures). This is the KEY DIFFERENCE from the Neo4j write pattern — do NOT wrap the entire `embed_chunks` call in a try/except that marks the document "failed". The per-chunk resilience lives inside `EmbeddingService.embed_chunks`.

5. **Tests run at 194 after Story 3.3** — all must continue to pass. The 6 new tests in this story should bring the total to ~200.

6. **Document status `String(20)`** — `"extracting_entities"` is 19 chars (the longest current status). `"embedding"` is 9 chars. No column width issue.

### Git Intelligence

Recent commits:
- `2e3c3b0` — fix: increase Ollama inference timeout to 300s (context: inference can be slow)
- `bdcd567` — feat: Story 3.2 — entity & relationship extraction via local LLM
- `c587e45` — Add README.md
- `18279df` — feat: Story 3.1 — document chunking & LLM integration layer with code review fixes

**Patterns to continue:**
- Services: class-based, `__init__` takes dependencies; no global state
- Celery task: sync everywhere (sync Neo4j, sync Qdrant, sync httpx via `httpx.Client`)
- Tests mirror source: `tests/services/test_embedding.py` ↔ `app/services/embedding.py`
- Exceptions: use existing `OllamaUnavailableError` — do not create a new `EmbeddingError`
- Logging: structured key-value pairs via `logger.info/warning/error("message", key=value, ...)`
- The `INFERENCE_TIMEOUT` was increased (to allow `read=None`) — embedding calls can also take time; re-use the same timeout

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Debug Log References

None — implementation was straightforward following the story spec.

### Completion Notes List

- Created `app/llm/embeddings.py` with `OllamaEmbeddingClient` — mirrors `OllamaClient` pattern; reuses `INFERENCE_TIMEOUT` imported from `app/llm/client.py`; raises `OllamaUnavailableError` on connect/timeout/HTTP errors.
- Updated `app/db/qdrant.py` — added `COLLECTION_NAME = "document_chunks"`, `VECTOR_SIZE = 4096`, and idempotent `ensure_qdrant_collection()` using `Distance.COSINE`.
- Created `app/services/embedding.py` with `EmbeddingService` and `EmbeddingSummary` dataclass — per-chunk failure handling: logs error and increments `failed_count` without aborting batch; returns final counts.
- Updated `app/worker/tasks/process_document.py` — replaced the final "All stages complete" block with Stage 4 (`embedding` status → `embed_chunks()` → `complete` status); `embedded_count` now included in `document.complete` event.
- Updated `app/main.py` lifespan — calls `ensure_qdrant_collection` via `asyncio.to_thread` after Neo4j constraints setup.
- 6 new tests in `tests/services/test_embedding.py`; all 200 tests pass.

### Senior Developer Review (AI)

**Date:** 2026-03-12 | **Reviewer:** Claude Sonnet 4.6

**Outcome:** Approved — 5 issues fixed during review

**Fixes applied:**
- **H2** `tests/services/test_embedding.py:46` — Added `collection_name` assertion to `test_embed_chunks_generates_and_upserts` (task 6.1 required it)
- **M1** `app/llm/embeddings.py:21` — Added `try/except (KeyError, IndexError)` around `data["embeddings"][0]`; malformed Ollama responses now raise `OllamaUnavailableError` with a clear message instead of a cryptic `KeyError`
- **M2** `app/worker/tasks/process_document.py` — Wrapped Stage 4 in `try/except Exception` matching the pattern of Stages 1–3; infrastructure failure (e.g. final DB commit) now marks document `"failed"` and publishes `document.failed` instead of leaving it stuck in `"embedding"`
- **M3** `app/llm/client.py` + `app/worker/tasks/process_document.py` — Made `check_available(model=DEFAULT_MODEL)` accept a model param; added pre-Stage 4 warning log when `qwen3-embedding:8b` is absent in Ollama
- **M4** `.gitignore` — Added `ollama_logs.txt` (and `*.log` pattern)

**Known process issue (H1):** Story 3.3 implementation files (`entities.py`, `entity_query.py`, `schemas/entity.py`, `test_entities.py`, `test_entity_query.py`, `router.py`, `exceptions.py`, `extraction.py`, `test_extraction.py`, `3-3-provenance-chain-evidence-storage.md`) are uncommitted and co-mingled in the working tree. Story 3.3 is marked `done` in sprint-status but its code has no git commit. These should be committed separately as Story 3.3 before committing Story 3.4.

### File List

apps/api/app/llm/embeddings.py (new)
apps/api/app/services/embedding.py (new)
apps/api/tests/services/test_embedding.py (new)
apps/api/app/db/qdrant.py (modified)
apps/api/app/worker/tasks/process_document.py (modified)
apps/api/app/llm/client.py (modified)
apps/api/app/main.py (modified)
.gitignore (modified)
_bmad-output/implementation-artifacts/sprint-status.yaml (modified)
_bmad-output/implementation-artifacts/3-4-vector-embedding-generation-storage.md (this file)
