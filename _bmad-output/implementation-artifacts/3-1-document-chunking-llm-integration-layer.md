# Story 3.1: Document Chunking & LLM Integration Layer

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want the document processing pipeline to chunk extracted text and communicate with Ollama,
so that entities can be extracted from manageable text segments with the local LLM.

## Acceptance Criteria

1. GIVEN a document has completed text extraction (status `complete` from Epic 2), WHEN the processing pipeline continues to the chunking stage, THEN the extracted text is split into chunks with page/passage tracking preserved, AND each chunk records its source document ID, page number(s), and character offsets, AND chunks are stored in PostgreSQL with their provenance metadata.
2. GIVEN the Ollama integration module exists at `app/llm/client.py`, WHEN a service calls the LLM client, THEN requests are sent to the local Ollama instance (model `qwen3.5:9b`), AND zero outbound network calls are made — all inference is local, AND the client uses structured JSON output via Ollama's `format` parameter.
3. GIVEN prompts are defined in `app/llm/prompts.py`, WHEN extraction or query services need LLM interaction, THEN prompts are loaded from that module (never hardcoded in services or tasks).
4. GIVEN Ollama is unavailable during chunk processing, WHEN the LLM client fails to connect, THEN the error is caught and logged via Loguru, AND the document status transitions to `failed` with a clear error message, AND a `document.failed` SSE event is published.
5. GIVEN a document with extracted text containing page markers (`--- Page N ---`), WHEN chunking splits the text, THEN each chunk preserves which page(s) it spans, AND overlapping chunks include content from adjacent segments to prevent entity loss at boundaries.
6. GIVEN the chunking stage completes, WHEN chunks are stored, THEN the document status transitions through a `chunking` stage (visible via SSE `document.processing` events with `stage: "chunking"`).

## Tasks / Subtasks

- [x] **Task 1: Create `DocumentChunk` SQLModel + Alembic migration** (AC: 1)
  - [x] 1.1: Create `app/models/chunk.py` with `DocumentChunk` model: `id` (UUID PK), `document_id` (FK → documents.id, cascade delete), `investigation_id` (UUID, indexed), `sequence_number` (int), `text` (Text), `page_start` (int), `page_end` (int), `char_offset_start` (int), `char_offset_end` (int), `token_count` (int | None), `created_at` (DateTime)
  - [x] 1.2: Add `DocumentChunk` import to `app/models/__init__.py`
  - [x] 1.3: Create Alembic migration `004_create_document_chunks_table.py` with composite index on `(document_id, sequence_number)` and index on `investigation_id`
  - [x] 1.4: Verify migration runs via `uv run alembic upgrade head`

- [x] **Task 2: Implement `ChunkingService`** (AC: 1, 5, 6)
  - [x] 2.1: Create `app/services/chunking.py` with `ChunkingService` class
  - [x] 2.2: Implement `chunk_document(document_id, investigation_id, extracted_text, session) -> list[DocumentChunk]`:
    - Parse page markers (`--- Page N ---`) to build page-indexed text segments
    - Split into chunks of ~1000 characters with ~200 character overlap
    - Track `page_start`, `page_end`, `char_offset_start`, `char_offset_end` per chunk
    - Assign sequential `sequence_number` starting at 0
    - Bulk-insert chunks into PostgreSQL
    - Return list of created chunks
  - [x] 2.3: Handle edge cases: empty text, single-page docs, text without page markers
  - [x] 2.4: Write unit tests in `tests/services/test_chunking.py`: multi-page chunking, single-page, empty text, overlap verification, provenance accuracy

- [x] **Task 3: Create Ollama LLM client** (AC: 2, 4)
  - [x] 3.1: Create `app/llm/client.py` with `OllamaClient` class
  - [x] 3.2: Use `httpx.Client` (sync, for Celery tasks) with `base_url` from `settings.ollama_base_url`
  - [x] 3.3: Implement `chat(model, messages, format=None, temperature=0) -> dict` — calls `POST /api/chat` with `stream=False`
  - [x] 3.4: Implement `generate(model, prompt, format=None, temperature=0) -> str` — calls `POST /api/generate` with `stream=False`
  - [x] 3.5: Implement `check_available() -> bool` — calls `GET /api/tags` and returns True if model `qwen3.5:9b` is in the list
  - [x] 3.6: Handle connection errors (`httpx.ConnectError`, `httpx.TimeoutException`) — raise `OllamaUnavailableError` with clear message
  - [x] 3.7: Configure timeout: 120s for chat/generate (LLM inference can be slow), 5s for check_available
  - [x] 3.8: Write unit tests in `tests/llm/test_client.py`: mock httpx responses for chat, generate, check_available, connection errors, timeout errors

- [x] **Task 4: Create prompt templates** (AC: 3)
  - [x] 4.1: Create `app/llm/prompts.py` with extraction prompt templates
  - [x] 4.2: Define `ENTITY_EXTRACTION_SYSTEM_PROMPT` — instructs LLM to extract entities (Person, Organization, Location) from text as JSON
  - [x] 4.3: Define `ENTITY_EXTRACTION_USER_PROMPT_TEMPLATE` — template accepting `{chunk_text}` variable
  - [x] 4.4: Define Pydantic response schema `EntityExtractionResponse` in `app/llm/schemas.py` for validating LLM JSON output: `entities: list[ExtractedEntity]` where `ExtractedEntity` has `name`, `type` (enum: person/organization/location), `confidence` (float 0-1)
  - [x] 4.5: Write tests in `tests/llm/test_prompts.py`: verify prompt templates are non-empty strings, response schema validates correct/incorrect JSON

- [x] **Task 5: Integrate chunking into document processing pipeline** (AC: 1, 4, 6)
  - [x] 5.1: Update `app/worker/tasks/process_document.py` to add chunking stage after text extraction:
    - After text extraction succeeds, publish `document.processing` event with `stage: "chunking"`
    - Call `ChunkingService.chunk_document(...)` with the sync session
    - On success, publish `document.processing` event with `stage: "chunking_complete"` and `chunk_count` in payload
    - On failure, set document status to `failed`, publish `document.failed` event
  - [x] 5.2: Update document status flow: `queued` → `extracting_text` → `chunking` → `complete` (for now; Story 3.2 adds `extracting_entities`, Story 3.4 adds `embedding`)
  - [x] 5.3: Add `OllamaClient.check_available()` call at start of pipeline — if Ollama is down, fail fast with clear error before spending time on chunking
  - [x] 5.4: Write integration tests in `tests/worker/test_process_document.py`: test chunking stage, Ollama unavailable handling, SSE event publishing

- [x] **Task 6: Add domain exceptions** (AC: 4)
  - [x] 6.1: Add `OllamaUnavailableError(DomainError)` to `app/exceptions.py` — status_code 503, error_type `ollama_unavailable`
  - [x] 6.2: Add `ChunkingError(DomainError)` to `app/exceptions.py` — status_code 422, error_type `chunking_failed`

## Dev Notes

### Chunking Strategy

The architecture defers chunking strategy to this story. Implementation:

**Algorithm — Fixed-size with overlap and page-awareness:**
- Target chunk size: ~1000 characters (~250 tokens for English text)
- Overlap: ~200 characters between consecutive chunks
- Page boundary awareness: parse `--- Page N ---` markers from PyMuPDF output (Story 2.3) to track page provenance
- Split on sentence boundaries when possible (split at `.` followed by space/newline near chunk boundary)
- Each chunk stores: `page_start`, `page_end` (which pages the chunk spans), `char_offset_start`, `char_offset_end` (character positions in the original extracted_text)

**Why 1000 chars:** Balance between context size for entity extraction and granularity for provenance. Too large = coarse provenance. Too small = entities split across chunks. 1000 chars with 200 overlap handles most entity mentions.

**Page marker parsing:**
```python
# PyMuPDF output format from Story 2.3 TextExtractionService:
# "--- Page 1 ---\ntext...\n\n--- Page 2 ---\ntext..."
# Split on regex: r'^--- Page (\d+) ---$' (multiline)
# Build list of (page_number, page_text, char_offset) tuples
# Then chunk across pages, tracking which pages each chunk spans
```

### Ollama Client Architecture

**Direct httpx, NOT the ollama Python package.** The architecture specifies `app/llm/client.py` as an Ollama HTTP client. Using raw httpx (already a dependency) avoids adding a new package and gives full control over request/response handling.

**Ollama REST API endpoints used:**
- `POST /api/chat` — Chat completions with messages array (for entity extraction)
- `POST /api/generate` — Single prompt generation (simpler interface for embeddings prep)
- `GET /api/tags` — List available models (for health check / availability)

**Structured JSON output via Ollama:**
```python
# Ollama supports format="json" to constrain output to valid JSON
response = httpx.post(f"{base_url}/api/chat", json={
    "model": "qwen3.5:9b",
    "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
    "format": "json",
    "stream": False,
    "options": {"temperature": 0}
})
```

**Sync client for Celery tasks:** Celery workers run synchronously. Use `httpx.Client` (not `httpx.AsyncClient`). The existing `process_document_task` already uses sync patterns (`SyncSessionLocal`).

### Processing Pipeline Update

Current pipeline (Stories 2.x):
```
queued → extracting_text → complete (or failed)
```

Updated pipeline (Story 3.1):
```
queued → extracting_text → chunking → complete (or failed)
```

Future pipeline (Stories 3.2-3.4 will extend):
```
queued → extracting_text → chunking → extracting_entities → embedding → complete
```

**Important:** Story 3.1 ends at `chunking → complete`. Stories 3.2 and 3.4 will insert `extracting_entities` and `embedding` stages between `chunking` and `complete`. Keep the pipeline extensible — use a list of stages that can be extended.

### SSE Events

Reuse existing `EventPublisher` from `app/services/events.py`. New event payloads:

```python
# Chunking stage started
publisher.publish(investigation_id, "document.processing", {
    "document_id": str(document_id),
    "stage": "chunking",
    "progress": 0.0
})

# Chunking complete
publisher.publish(investigation_id, "document.processing", {
    "document_id": str(document_id),
    "stage": "chunking_complete",
    "chunk_count": len(chunks)
})
```

### Project Structure Notes

**Files to create:**
- `apps/api/app/models/chunk.py` — DocumentChunk SQLModel
- `apps/api/app/services/chunking.py` — ChunkingService
- `apps/api/app/llm/client.py` — OllamaClient
- `apps/api/app/llm/prompts.py` — Prompt templates
- `apps/api/app/llm/schemas.py` — Pydantic response schemas for LLM output
- `apps/api/migrations/versions/004_create_document_chunks_table.py` — Migration
- `apps/api/tests/services/test_chunking.py` — Chunking tests
- `apps/api/tests/llm/__init__.py` — Test package
- `apps/api/tests/llm/test_client.py` — OllamaClient tests
- `apps/api/tests/llm/test_prompts.py` — Prompt/schema tests

**Files to modify:**
- `apps/api/app/models/__init__.py` — Add DocumentChunk import
- `apps/api/app/exceptions.py` — Add OllamaUnavailableError, ChunkingError
- `apps/api/app/worker/tasks/process_document.py` — Add chunking stage to pipeline
- `apps/api/app/llm/__init__.py` — Add exports (client exists as empty file)

### Existing Code to Reuse (DO NOT REINVENT)

| What | Where | How to Reuse |
|------|-------|--------------|
| Document model with `extracted_text` | `app/models/document.py` | Read extracted_text for chunking input |
| `SyncSessionLocal` | `app/db/sync_postgres.py` | Use in Celery task for chunk storage |
| `EventPublisher` | `app/services/events.py` | Publish chunking stage SSE events |
| `TextExtractionService` page markers | `app/services/text_extraction.py` | Parse `--- Page N ---` format |
| `process_document_task` pattern | `app/worker/tasks/process_document.py` | Extend with chunking stage |
| `DomainError` base class | `app/exceptions.py` | Inherit for OllamaUnavailableError, ChunkingError |
| `settings.ollama_base_url` | `app/config.py` | Already configured: `http://ollama:11434` |
| `Base` model class | `app/models/base.py` | Inherit for DocumentChunk model |
| Existing migration patterns | `migrations/versions/001-003` | Follow same structure for migration 004 |
| `conftest.py` fixtures | `tests/conftest.py` | mock_postgres, sample_document, etc. |
| Loguru logging | Used throughout codebase | `logger.info(...)`, `logger.error(...)` with structured context |

### Anti-Patterns to Avoid

- **DO NOT** install the `ollama` Python package — use `httpx.Client` directly (already a dependency)
- **DO NOT** hardcode prompts in service files or tasks — all prompts in `app/llm/prompts.py`
- **DO NOT** use async httpx client in Celery tasks — Celery workers are sync; use `httpx.Client`
- **DO NOT** make outbound network calls — Ollama runs locally in Docker at `http://ollama:11434`
- **DO NOT** chunk by splitting on every newline — use fixed-size with overlap to preserve entity context
- **DO NOT** create a separate Celery task for chunking — extend the existing `process_document_task` pipeline
- **DO NOT** store chunks in Neo4j — chunks go in PostgreSQL; Neo4j is for entities/relationships (Story 3.2)
- **DO NOT** implement entity extraction in this story — that's Story 3.2. Only create the LLM client and prompts.
- **DO NOT** implement embedding generation — that's Story 3.4
- **DO NOT** add new Python packages to pyproject.toml — httpx and all needed deps are already installed
- **DO NOT** use `print()` — use Loguru `logger` for all output
- **DO NOT** create auto-increment IDs — use UUID v4 for chunk IDs

### Testing Standards

**Backend (pytest):**
- `test_chunking.py`: multi-page document chunking (verify page tracking, overlap, char offsets), single-page document, empty text handling, text without page markers, chunk count verification
- `test_client.py`: mock httpx for all Ollama endpoints — successful chat completion, successful generate, model list, connection error raises OllamaUnavailableError, timeout raises OllamaUnavailableError
- `test_prompts.py`: prompt templates are non-empty strings with expected variables, EntityExtractionResponse schema validates correct JSON, rejects malformed JSON
- `test_process_document.py`: extend existing tests for chunking stage — verify chunks stored after text extraction, verify SSE events for chunking stage, verify Ollama unavailable fails document gracefully

**Test pattern — mock httpx for Ollama tests:**
```python
from unittest.mock import patch, MagicMock
import httpx

@patch("app.llm.client.httpx.Client")
def test_chat_success(mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
    mock_client.post.return_value = httpx.Response(200, json={
        "message": {"role": "assistant", "content": '{"entities": []}'},
        "done": True
    })
    # ... test OllamaClient.chat(...)
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Epic 3, Story 3.1 acceptance criteria]
- [Source: _bmad-output/planning-artifacts/architecture.md — LLM module: app/llm/client.py, prompts.py, embeddings.py]
- [Source: _bmad-output/planning-artifacts/architecture.md — Ollama config: qwen3.5:9b, base URL, Docker service]
- [Source: _bmad-output/planning-artifacts/architecture.md — SSE event types: document.processing, document.failed]
- [Source: _bmad-output/planning-artifacts/architecture.md — Processing pipeline stages]
- [Source: _bmad-output/planning-artifacts/architecture.md — Naming conventions: snake_case columns, UUID IDs]
- [Source: _bmad-output/planning-artifacts/architecture.md — Deferred: chunking strategy to story-level]
- [Source: _bmad-output/planning-artifacts/prd.md — FR11-FR16: Entity extraction requirements]
- [Source: _bmad-output/planning-artifacts/prd.md — NFR1: 100-page PDF processed in <15 min]
- [Source: _bmad-output/planning-artifacts/prd.md — NFR14-NFR16: Zero outbound calls, local LLM only]
- [Source: apps/api/app/worker/tasks/process_document.py — Existing pipeline: queued → extracting_text → complete]
- [Source: apps/api/app/services/text_extraction.py — PyMuPDF page marker format: "--- Page N ---"]
- [Source: apps/api/app/services/events.py — EventPublisher for Redis pub/sub SSE]
- [Source: apps/api/app/config.py — ollama_base_url: http://ollama:11434]
- [Source: apps/api/app/db/sync_postgres.py — SyncSessionLocal for Celery sync tasks]
- [Source: apps/api/app/exceptions.py — DomainError base class pattern]
- [Source: apps/api/pyproject.toml — httpx already installed, no ollama package needed]
- [Source: _bmad-output/implementation-artifacts/2-5-extracted-text-viewer.md — Previous story patterns and conventions]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- httpx.Response mock required `request` attribute for `raise_for_status()` — switched to MagicMock-based responses in test_client.py

### Completion Notes List

- **Task 1:** Created `DocumentChunk` model with UUID PK, FK to documents, investigation_id index, composite index on (document_id, sequence_number). Migration 004 verified syntactically valid.
- **Task 2:** Implemented ChunkingService with fixed-size (~1000 char) overlap (~200 char) chunking. Page marker parsing via regex. Sentence boundary splitting. Edge cases handled: empty text, whitespace-only, no page markers, single page. 10 unit tests pass.
- **Task 3:** Created OllamaClient with sync httpx.Client for Celery tasks. Implements chat(), generate(), check_available(). 120s timeout for inference, 5s for health checks. Raises OllamaUnavailableError on connection/timeout errors. 10 unit tests pass.
- **Task 4:** Created entity extraction prompt templates in prompts.py and Pydantic response schemas (EntityExtractionResponse, ExtractedEntity with enum type and bounded confidence) in schemas.py. 11 tests pass.
- **Task 5:** Extended process_document_task pipeline: Ollama availability check (fail-fast) → text extraction → chunking → complete. SSE events published for each stage. Chunking failure gracefully sets document to failed. 8 integration tests pass.
- **Task 6:** Added OllamaUnavailableError (503) and ChunkingError (422) to exceptions.py, following existing DomainError pattern.
- **Full suite:** 137 tests pass, 0 regressions.

### Change Log

- 2026-03-09: Story 3.1 implementation complete — document chunking, LLM client, prompt templates, pipeline integration
- 2026-03-10: Code review fixes applied — H1/H2: HTTPStatusError now caught in all OllamaClient methods; H3: session.rollback() added before chunking failure commit; M1: infinite loop guard fixed (same coordinate space); M2: fallback offset corrected to content_start, dead code removed; M3: composite index added to DocumentChunk.__table_args__. 6 new tests added. 43/43 pass.

### File List

**New files:**
- apps/api/app/models/chunk.py
- apps/api/app/services/chunking.py
- apps/api/app/llm/client.py
- apps/api/app/llm/prompts.py
- apps/api/app/llm/schemas.py
- apps/api/migrations/versions/004_create_document_chunks_table.py
- apps/api/tests/services/test_chunking.py
- apps/api/tests/llm/__init__.py
- apps/api/tests/llm/test_client.py
- apps/api/tests/llm/test_prompts.py

**Modified files:**
- apps/api/app/models/__init__.py
- apps/api/app/exceptions.py
- apps/api/app/worker/tasks/process_document.py
- apps/api/tests/worker/test_process_document.py
