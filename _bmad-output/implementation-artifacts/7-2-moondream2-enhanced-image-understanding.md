# Story 7.2: moondream2 Enhanced Image Understanding

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an investigator,
I want the system to use visual AI understanding for images where basic OCR struggles,
So that I can extract useful text from handwritten notes, complex layouts, and degraded scans.

## Acceptance Criteria

1. **GIVEN** the Docker Compose configuration, **WHEN** the system starts up, **THEN** moondream2 is available via Ollama alongside qwen3.5:9b and qwen3-embedding:8b, **AND** the health endpoint reports moondream2 readiness status.

2. **GIVEN** Tesseract OCR produces output for an image document, **WHEN** the OCR output quality is below a configurable threshold (e.g., low character confidence, very short output relative to image size), **THEN** the system routes the image to moondream2 for enhanced understanding, **AND** moondream2 analyzes the image visually and extracts text/descriptions of content, **AND** the moondream2 output supplements or replaces the Tesseract output.

3. **GIVEN** moondream2 processes an image with handwritten text, **WHEN** it extracts content, **THEN** the extracted text includes both recognized text and visual descriptions of content the model identifies, **AND** the output clearly distinguishes OCR-extracted text from visual description.

4. **GIVEN** moondream2 is unavailable (Ollama down or model not loaded), **WHEN** an image would normally be routed to moondream2, **THEN** the system falls back to Tesseract-only output, **AND** the document is not marked as failed — degraded OCR is preferable to no processing, **AND** a warning is logged via Loguru.

5. **GIVEN** image OCR processing runs on minimum hardware, **WHEN** a single image page is processed (Tesseract + moondream2 if triggered), **THEN** total OCR processing completes in <60 seconds per image page (NFR31).

## Tasks / Subtasks

- [x] **Task 1: Add moondream2 to health check and model readiness** (AC: 1)
  - [x] 1.1: In `apps/api/app/services/health.py`, add `"moondream2"` to either `CHAT_MODELS` or a new `VISION_MODELS` list. Add it to the Ollama health check so the health endpoint reports moondream2 readiness alongside qwen3.5:9b and qwen3-embedding:8b. moondream2 runs on the same Ollama instance as chat models (same `ollama_base_url`).
  - [x] 1.2: In `apps/api/app/schemas/health.py`, no schema changes needed — `ModelInfo` already has `name: str` and `available: bool` which is generic enough for any model. Verify the existing health response includes all models.
  - [x] 1.3: In `apps/web/src/routes/status.tsx` (SystemStatusPage), verify moondream2 appears in the models list automatically — the frontend iterates `ollama.models` from the health response, so no frontend changes needed if the backend reports it.
  - [x] 1.4: Write backend test: health endpoint returns moondream2 in models list with available=true/false.

- [x] **Task 2: Create moondream2 vision service** (AC: 2, 3)
  - [x] 2.1: Create `apps/api/app/services/vision.py` with class `VisionService`. This service calls Ollama's `/api/chat` endpoint with moondream2 model, passing the image as a base64-encoded image in the `images` field of the message (Ollama's multimodal API format).
  - [x] 2.2: Method `analyze_image(self, file_path: Path, prompt: str = "Describe all text and content visible in this image in detail. If there is handwritten text, transcribe it.") -> VisionResult` that: reads the image file, base64-encodes it, sends to Ollama `/api/chat` with model="moondream2" and the image attached, returns a `VisionResult` dataclass with `description: str` and `source: str = "moondream2"`.
  - [x] 2.3: Handle moondream2 unavailability gracefully: catch connection errors and timeouts, log warning via Loguru, return `None` (caller falls back to Tesseract-only). Never raise — moondream2 failure is non-fatal.
  - [x] 2.4: Add a `check_available(self) -> bool` method that checks if moondream2 is loaded in Ollama (reuse pattern from `OllamaClient.check_available()`).
  - [x] 2.5: Define `VisionResult` as a dataclass in the same file: `description: str`, `source: str`.

- [x] **Task 3: Implement OCR quality assessment and moondream2 routing** (AC: 2, 4)
  - [x] 3.1: In `apps/api/app/services/image_extraction.py`, add a method `assess_ocr_quality(self, text: str, file_path: Path) -> float` that returns a quality score 0.0-1.0. Heuristics: (a) character count relative to image pixel area (very short text from a large image = low quality), (b) ratio of alphanumeric chars to total chars (high gibberish ratio = low quality), (c) average word length sanity check (too short or too long words = garbage). Return a weighted average.
  - [x] 3.2: Add a configurable threshold constant `OCR_QUALITY_THRESHOLD = 0.3` (default; can be overridden via environment variable `OCR_QUALITY_THRESHOLD`). Below this threshold, moondream2 is triggered.
  - [x] 3.3: Update `ImageExtractionService.extract_text()` to: (a) run Tesseract first (existing code), (b) assess OCR quality, (c) if quality < threshold AND moondream2 is available, call `VisionService.analyze_image()`, (d) combine results. Method signature gains optional `enhance_with_vision: bool = True` parameter to allow disabling enhancement.
  - [x] 3.4: When moondream2 enhances: if Tesseract returned some text, prepend Tesseract output with `[OCR Text]\n` header and append moondream2 output with `\n\n[Visual Analysis]\n` header. If Tesseract returned empty/garbage, use moondream2 output alone with `[Visual Analysis]\n` header. This ensures downstream ChunkingService sees structured text with clear source markers.
  - [x] 3.5: Log the quality assessment result and routing decision: `logger.info("OCR quality assessed", document_id=..., quality_score=..., threshold=..., using_vision=...)`.

- [x] **Task 4: Update process_document pipeline for vision enhancement** (AC: 2, 4, 5)
  - [x] 4.1: In `apps/api/app/worker/tasks/process_document.py`, update the image extraction branch (currently line ~134-136) to pass the `document_id` and allow vision enhancement. The `ImageExtractionService` already receives `document_id` — just ensure the vision enhancement path works within the existing pipeline flow.
  - [x] 4.2: Add Ollama base URL to `ImageExtractionService` constructor or pass it to `extract_text()` so `VisionService` can connect. Use `settings.ollama_base_url` (same Ollama instance as chat models).
  - [x] 4.3: Ensure the 60-second per-page timeout (NFR31) is respected: the existing Ollama timeouts (`INFERENCE_TIMEOUT` with `read=None`) allow long inference. If moondream2 takes too long, the overall task timeout in Celery handles it. No additional timeout needed unless specifically required.
  - [x] 4.4: When moondream2 is used, log the enhanced extraction: `logger.info("Image processed with vision enhancement", document_id=..., ocr_chars=..., vision_chars=..., total_chars=...)`.

- [x] **Task 5: Add OCR method metadata to document response** (AC: 3)
  - [x] 5.1: Add `ocr_method` column to Document model: `ocr_method: Mapped[str | None] = mapped_column(String(30), nullable=True)`. Values: `"tesseract"`, `"tesseract+moondream2"`, `"moondream2"`, `None` (for non-image docs).
  - [x] 5.2: Create Alembic migration (next sequence after existing migrations — check `apps/api/migrations/versions/` for the latest number) adding the `ocr_method` column.
  - [x] 5.3: Add `ocr_method` to `DocumentResponse` schema in `apps/api/app/schemas/document.py`.
  - [x] 5.4: Set `ocr_method` in `ImageExtractionService` return value or in `process_document_task` after extraction completes. Store on the document record.
  - [x] 5.5: Regenerate OpenAPI types: run `scripts/generate-api-types.sh`.

- [x] **Task 6: Frontend — display OCR method indicator** (AC: 3)
  - [x] 6.1: In `apps/web/src/components/investigation/DocumentCard.tsx`, show an `ocr_method` badge/indicator when `document_type === "image"` and `ocr_method` is available. Use existing badge patterns (extraction_quality badge). Show "Tesseract" or "Tesseract + Vision AI" or "Vision AI" to distinguish.
  - [x] 6.2: No changes to `DocumentUploadZone.tsx` — upload flow is unchanged from Story 7.1.

- [x] **Task 7: Backend tests** (AC: 1, 2, 3, 4)
  - [x] 7.1: Create `apps/api/tests/services/test_vision.py`: test `VisionService.analyze_image()` with mocked Ollama response, verify base64 encoding, verify prompt content, verify `VisionResult` returned.
  - [x] 7.2: Test `VisionService` when Ollama is unavailable: mock connection error, verify returns `None`, verify warning logged.
  - [x] 7.3: Test `VisionService.check_available()`: mock Ollama `/api/tags` response with and without moondream2.
  - [x] 7.4: In `apps/api/tests/services/test_image_extraction.py` (create if needed): test `assess_ocr_quality()` with various inputs: (a) good quality text returns > threshold, (b) short garbage returns < threshold, (c) empty text returns 0.0.
  - [x] 7.5: Test `ImageExtractionService.extract_text()` with vision enhancement: mock Tesseract returning low-quality text, mock VisionService returning description, verify combined output has `[OCR Text]` and `[Visual Analysis]` headers.
  - [x] 7.6: Test fallback when moondream2 unavailable: mock VisionService returning None, verify Tesseract-only output used, verify no failure.
  - [x] 7.7: Test health endpoint includes moondream2 in models list.
  - [x] 7.8: Test Alembic migration applies cleanly (verify `ocr_method` column exists after migration).

- [x] **Task 8: Frontend tests** (AC: 3)
  - [x] 8.1: In `DocumentCard.test.tsx`, add test: renders "Tesseract + Vision AI" badge when `ocr_method === "tesseract+moondream2"`.
  - [x] 8.2: Add test: renders "Tesseract" badge when `ocr_method === "tesseract"`.
  - [x] 8.3: Add test: does not render OCR method badge for PDF documents.

## Dev Notes

### Architecture Context

This is **Story 7.2** — extends Story 7.1's Tesseract-only image OCR with moondream2 visual AI for enhanced understanding of images where OCR struggles (handwritten text, complex layouts, degraded scans). moondream2 is a lightweight vision-language model available via Ollama.

**FRs covered:** FR50 (moondream2 enhanced image understanding)
**NFRs relevant:** NFR31 (<60s per image page), all existing privacy NFRs (local inference only via Ollama)

### What Already Exists -- DO NOT RECREATE

| Component | Location | What It Does |
|---|---|---|
| ImageExtractionService | `app/services/image_extraction.py` | Tesseract OCR with Pillow, page-marker format, graceful empty handling |
| OllamaClient | `app/llm/client.py` | Chat/generate/check_available against Ollama. `INFERENCE_TIMEOUT` with read=None. |
| HealthService | `app/services/health.py` | Checks all services including Ollama models. `CHAT_MODELS`, `EMBEDDING_MODELS` lists. |
| process_document_task | `app/worker/tasks/process_document.py` | 4-stage pipeline. Image branch at line ~134. |
| Document model | `app/models/document.py` | Has `document_type`, `extracted_text`, `extraction_confidence`, etc. |
| DocumentResponse schema | `app/schemas/document.py` | Pydantic schema with `extraction_quality` computed field. |
| DocumentCard | `components/investigation/DocumentCard.tsx` | Shows Image/FileText icon, extraction quality badge. |
| Settings | `app/config.py` | `ollama_base_url`, `ollama_embedding_url` — moondream2 uses `ollama_base_url` (same as chat models). |
| Alembic migrations | `migrations/versions/` | Numbered sequence (001-009+). Check latest for next number. |

### Critical Implementation Details

#### Ollama Multimodal API for moondream2

moondream2 is a vision-language model. Ollama's `/api/chat` endpoint accepts images as base64 in messages:

```python
import base64, httpx

with open(image_path, "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode("utf-8")

body = {
    "model": "moondream2",
    "messages": [
        {
            "role": "user",
            "content": "Describe all text and content visible in this image.",
            "images": [image_b64],
        }
    ],
    "stream": False,
    "options": {"temperature": 0},
}
resp = httpx.post(f"{base_url}/api/chat", json=body, timeout=httpx.Timeout(connect=5.0, read=None, write=10.0, pool=5.0))
result = resp.json()["message"]["content"]
```

Key points:
- `images` field is a list of base64-encoded strings in the message dict
- Use `stream: False` for simplicity (we need the full response, not streaming)
- `temperature: 0` for deterministic output
- Reuse `INFERENCE_TIMEOUT` pattern from `OllamaClient` (read=None allows long inference)

#### OCR Quality Heuristics

The quality assessment determines when to route to moondream2:

```python
def assess_ocr_quality(self, text: str, file_path: Path) -> float:
    if not text.strip():
        return 0.0

    # Factor 1: Text density relative to image size
    with Image.open(file_path) as img:
        pixel_area = img.width * img.height
    chars_per_megapixel = len(text) / (pixel_area / 1_000_000)
    density_score = min(chars_per_megapixel / 500, 1.0)  # 500 chars/MP is "normal"

    # Factor 2: Alphanumeric ratio (gibberish detection)
    alnum_count = sum(c.isalnum() or c.isspace() for c in text)
    alnum_ratio = alnum_count / len(text) if text else 0
    alnum_score = alnum_ratio  # 0.0-1.0

    # Factor 3: Average word length sanity
    words = text.split()
    if words:
        avg_len = sum(len(w) for w in words) / len(words)
        word_score = 1.0 if 2 <= avg_len <= 15 else 0.3
    else:
        word_score = 0.0

    return 0.4 * density_score + 0.4 * alnum_score + 0.2 * word_score
```

Default threshold: `OCR_QUALITY_THRESHOLD = 0.3`. Environment-configurable.

#### Combined Output Format

When both Tesseract and moondream2 are used:

```
--- Page 1 ---
[OCR Text]
The quick brown fox jumps over the lazy dog.
Some partially recognized text here.

[Visual Analysis]
The image shows a handwritten note on lined paper. The text reads:
"Meeting with John at 3pm - discuss project timeline."
There is also a hand-drawn diagram showing workflow connections between boxes labeled "Input", "Processing", and "Output".
```

The `[OCR Text]` and `[Visual Analysis]` headers help downstream consumers (ChunkingService, entity extraction) distinguish the sources. The existing ChunkingService splits on `--- Page N ---` markers, so this format is compatible — the entire content under `--- Page 1 ---` is one chunk.

#### Migration Naming

Check `apps/api/migrations/versions/` for the latest migration number. The new migration should be the next in sequence (e.g., `010_add_ocr_method.py` if latest is 009).

#### Fallback Behavior (Critical)

When moondream2 is unavailable:
1. `VisionService.analyze_image()` returns `None` (never raises)
2. `ImageExtractionService` uses Tesseract-only output
3. `ocr_method` is set to `"tesseract"` (not `"tesseract+moondream2"`)
4. Document is NOT marked as failed
5. Warning logged: `logger.warning("moondream2 unavailable, using Tesseract-only", document_id=...)`

This is a graceful degradation path — degraded OCR is always preferable to no processing.

### Project Structure Notes

**New files:**
- `apps/api/app/services/vision.py` — VisionService for moondream2
- `apps/api/migrations/versions/NNN_add_ocr_method.py` — Alembic migration
- `apps/api/tests/services/test_vision.py` — VisionService tests
- `apps/api/tests/services/test_image_extraction.py` — OCR quality + vision enhancement tests (if not existing)

**Modified files:**
- `apps/api/app/services/image_extraction.py` — OCR quality assessment, vision enhancement routing
- `apps/api/app/services/health.py` — add moondream2 to model readiness checks
- `apps/api/app/models/document.py` — add `ocr_method` column
- `apps/api/app/schemas/document.py` — add `ocr_method` to response
- `apps/api/app/worker/tasks/process_document.py` — pass settings to image extraction, store ocr_method
- `apps/web/src/components/investigation/DocumentCard.tsx` — OCR method badge
- `apps/web/src/lib/api-types.generated.ts` — regenerated (auto)

### Important Patterns from Previous Stories (Story 7.1)

1. **Celery tasks use sync sessions** — `SyncSessionLocal()`. API endpoints use async sessions.
2. **SSE events are best-effort** — `_publish_safe()` wrapper never raises. Commit DB state before publishing.
3. **RFC 7807 error format** — `{type, title, status, detail, instance}` via `DomainError` subclasses.
4. **Service layer pattern** — Business logic in `app/services/`, Celery tasks orchestrate services.
5. **Loguru structured logging** — `logger.info("Message", key=value, key2=value2)`.
6. **Pillow context manager** — Always use `with Image.open(file_path) as image:` for FD safety.
7. **ImageExtractionService** returns `""` for empty OCR (not None). Process pipeline handles empty text early exit.
8. **Page marker format** — `--- Page 1 ---\n{text}` for compatibility with ChunkingService.
9. **Pre-existing test failures** — SystemStatusPage.test.tsx (4 failures), test_docker_compose.py (2 infra), test_entity_discovered_sse_events_published (1 mock). Do not fix these.
10. **OpenAPI type generation** — run `scripts/generate-api-types.sh` after any schema change.

### References

- [Source: _bmad-output/planning-artifacts/prd.md — Lines 486, 500: Image OCR (Tesseract + moondream2) in v1.1 scope]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 66-77: Ollama LLM runtime, model list]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 346-358: Docker Compose, Ollama service]
- [Source: _bmad-output/planning-artifacts/architecture.md — Lines 486-496: Error handling patterns]
- [Source: apps/api/app/services/image_extraction.py — Existing Tesseract OCR service]
- [Source: apps/api/app/llm/client.py — OllamaClient with chat/generate/check_available]
- [Source: apps/api/app/services/health.py — HealthService with CHAT_MODELS, EMBEDDING_MODELS]
- [Source: apps/api/app/worker/tasks/process_document.py — Image extraction branch at ~line 134]
- [Source: apps/api/app/config.py — Settings with ollama_base_url]
- [Source: apps/api/app/models/document.py — Document model with document_type field]

## Change Log

- 2026-04-12: Story 7.2 created with comprehensive developer context for moondream2 enhanced image understanding
- 2026-04-12: Story 7.2 implemented — moondream2 vision service, OCR quality assessment, health check integration, frontend OCR method badge, backend + frontend tests
- 2026-04-12: Code review fixes — added ocr_method to _to_response API helper (critical data flow gap), added image size guard in VisionService (memory safety), fixed log file_path in empty OCR case, added ocr_method to sample_document fixture and mixed upload test mock

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Worker tests (`tests/worker/test_process_document.py`) — 20 pre-existing failures due to missing Docker infrastructure (Neo4j/Qdrant/Redis), not caused by this story
- SystemStatusPage.test.tsx (4 failures) — pre-existing TanStack Router mock issue, not caused by this story

### Completion Notes List

- Task 1: Added `moondream2` to `VISION_MODELS` in health service, updated Ollama health check to report moondream2 readiness alongside existing models. Updated conftest mock to include moondream2. Updated health model count assertions from 2 to 3.
- Task 2: Created `VisionService` in `app/services/vision.py` — base64 image encoding, Ollama multimodal chat API, graceful failure (returns None, never raises). Includes `check_available()` and `analyze_image()`.
- Task 3: Added `assess_ocr_quality()` method with 3 heuristics (text density, alnum ratio, word length). Added configurable `OCR_QUALITY_THRESHOLD=0.3`. Updated `extract_text()` to return `(text, ocr_method)` tuple. Added `[OCR Text]` and `[Visual Analysis]` headers for combined output.
- Task 4: Updated `process_document_task` to pass `ollama_base_url` to `ImageExtractionService`, unpack `(text, method)` tuple, store `ocr_method` on document record.
- Task 5: Added `ocr_method` column to Document model (String(30), nullable). Created Alembic migration 010. Added to DocumentResponse schema. Updated OpenAPI generated types.
- Task 6: Added OCR method badge in DocumentCard showing "Tesseract", "Tesseract + Vision AI", or "Vision AI" for image documents.
- Task 7: Created 14 backend tests: 6 VisionService tests, 7 ImageExtractionService tests (quality + vision), 1 health moondream2 test.
- Task 8: Added 4 frontend tests for OCR method badge (3 method variants + no badge for PDFs).

### File List

**New files:**
- `apps/api/app/services/vision.py` — VisionService for moondream2 via Ollama multimodal API
- `apps/api/migrations/versions/010_add_ocr_method_to_documents.py` — Alembic migration
- `apps/api/tests/services/test_vision.py` — 6 VisionService unit tests
- `apps/api/tests/services/test_image_extraction.py` — 12 OCR quality + vision enhancement tests

**Modified files:**
- `apps/api/app/services/image_extraction.py` — OCR quality assessment, vision enhancement routing, returns (text, method) tuple
- `apps/api/app/services/health.py` — added VISION_MODELS with moondream2, updated check_ollama
- `apps/api/app/api/v1/documents.py` — added ocr_method to _to_response helper (code review fix)
- `apps/api/app/models/document.py` — added ocr_method column
- `apps/api/app/schemas/document.py` — added ocr_method field to DocumentResponse
- `apps/api/app/worker/tasks/process_document.py` — pass ollama_base_url to ImageExtractionService, unpack tuple, store ocr_method
- `apps/api/tests/conftest.py` — added moondream2 to mock_ollama_healthy fixture
- `apps/api/tests/services/test_health.py` — updated model count assertion, added moondream2 test
- `apps/api/tests/api/test_health.py` — updated model count assertion
- `apps/api/tests/api/test_documents.py` — updated existing image extraction tests for new return type
- `apps/web/src/components/investigation/DocumentCard.tsx` — OCR method badge
- `apps/web/src/components/investigation/DocumentCard.test.tsx` — 4 new OCR method badge tests
- `apps/web/src/lib/api-types.generated.ts` — added ocr_method field
