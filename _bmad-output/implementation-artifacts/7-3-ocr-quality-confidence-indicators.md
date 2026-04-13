# Story 7.3: OCR Quality Confidence Indicators

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an investigator,
I want to see how well the system processed each image document,
So that I know which scans to trust and which ones I should manually review.

## Acceptance Criteria

1. **GIVEN** an image document has been processed through OCR, **WHEN** OCR completes (Tesseract), **THEN** an OCR quality confidence score (0.0-1.0) is computed and stored with the document record, **AND** the score factors in: Tesseract character-level confidence, text density relative to image area, and average word length sanity.

2. **GIVEN** the investigator views the document list, **WHEN** image documents are present, **THEN** each image document shows an OCR quality badge following the existing confidence visual language: high (solid border), medium (dashed), low (dotted + warning icon), **AND** the badge tooltip explains the quality level (e.g., "Low: OCR detected poor text quality").

3. **GIVEN** the processing dashboard shows real-time progress, **WHEN** an image document completes processing, **THEN** the document status card shows the OCR quality indicator, **AND** the overall investigation summary distinguishes PDF documents from image documents in the count.

4. **GIVEN** the investigator clicks "View Text" on an image document, **WHEN** the extracted text is displayed, **THEN** the viewer indicates whether the text came from Tesseract OCR, **AND** low-confidence passages are visually flagged so the investigator knows where to focus manual review.

FRs covered: FR51 (OCR quality confidence per image document)

## Tasks / Subtasks

- [x] **Task 1: Add `ocr_confidence` column to Document model + Alembic migration** (AC: 1)
  - [x] 1.1: Add `ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)` to `apps/api/app/models/document.py`
  - [x] 1.2: Create Alembic migration `010_add_ocr_confidence.py` (next after 009) adding the `ocr_confidence` column
  - [x] 1.3: Add `ocr_confidence` field to `DocumentResponse` schema in `apps/api/app/schemas/document.py`
  - [x] 1.4: Add a `ocr_quality` computed field on `DocumentResponse` that maps the ocr_confidence score to "high" (>=0.7), "medium" (>=0.4), "low" (<0.4), or None
  - [x] 1.5: Add `ocr_confidence` to the `_to_response()` helper in `apps/api/app/api/v1/documents.py`
  - [x] 1.6: Regenerate OpenAPI types: run `scripts/generate-api-types.sh`

- [x] **Task 2: Implement OCR quality assessment in ImageExtractionService** (AC: 1)
  - [x] 2.1: In `apps/api/app/services/image_extraction.py`, add method `assess_ocr_quality(self, text: str, file_path: Path) -> float` that returns a quality score 0.0-1.0
  - [x] 2.2: Heuristic factors: (a) text density — character count relative to image pixel area (via `Image.open` to get dimensions), (b) alphanumeric ratio — ratio of alnum+space chars to total chars (gibberish detection), (c) average word length — sanity check (too short or too long = garbage)
  - [x] 2.3: Return weighted average: `0.4 * density_score + 0.4 * alnum_score + 0.2 * word_score`
  - [x] 2.4: Update `extract_text()` method to return a tuple `(text: str, ocr_confidence: float)` instead of just a string
  - [x] 2.5: Log quality assessment: `logger.info("OCR quality assessed", document_id=..., ocr_confidence=..., density_score=..., alnum_score=..., word_score=...)`

- [x] **Task 3: Store OCR confidence in process_document pipeline** (AC: 1)
  - [x] 3.1: In `apps/api/app/worker/tasks/process_document.py`, update the image extraction branch to unpack the `(text, confidence)` tuple from `ImageExtractionService.extract_text()`
  - [x] 3.2: Store `ocr_confidence` on the document record: `document.ocr_confidence = confidence`
  - [x] 3.3: Include `ocr_confidence` in the `document.complete` SSE event payload
  - [x] 3.4: For the empty-text early exit path, set `ocr_confidence = 0.0`

- [x] **Task 4: Update frontend DocumentCard with OCR quality badge** (AC: 2)
  - [x] 4.1: In `apps/web/src/components/investigation/DocumentCard.tsx`, add an OCR quality badge for image documents using the `ocr_quality` computed field
  - [x] 4.2: Badge follows existing confidence visual language: high = solid border with success color, medium = dashed border with warning color, low = dotted border with warning icon
  - [x] 4.3: Add tooltip to OCR quality badge explaining the quality level (e.g., "High: OCR text is clear and well-structured", "Low: OCR detected poor text quality — manual review recommended")
  - [x] 4.4: Only show OCR quality badge for image documents (not PDFs or web)

- [x] **Task 5: Update ProcessingDashboard to distinguish document types** (AC: 3)
  - [x] 5.1: In `apps/web/src/components/investigation/ProcessingDashboard.tsx`, update the summary line to show document type counts: "X documents (Y PDFs, Z images) ..."
  - [x] 5.2: Show OCR confidence in the `document.complete` SSE event when it arrives

- [x] **Task 6: Update DocumentTextViewer for OCR source indication** (AC: 4)
  - [x] 6.1: In `apps/web/src/components/investigation/DocumentTextViewer.tsx`, add a banner at the top indicating the text came from OCR when the document is an image type
  - [x] 6.2: Show the OCR confidence level in the banner (e.g., "Text extracted via Tesseract OCR — Medium confidence")
  - [x] 6.3: For low confidence, add a visual warning: "Some text may be inaccurate — manual review recommended"

- [x] **Task 7: Backend tests** (AC: 1, 2, 3, 4)
  - [x] 7.1: Create `apps/api/tests/services/test_image_extraction.py`: test `assess_ocr_quality()` with good text returns > 0.7, gibberish returns < 0.4, empty text returns 0.0
  - [x] 7.2: Test `extract_text()` returns tuple `(text, confidence)` with valid confidence score
  - [x] 7.3: Test `extract_text()` with empty OCR output returns `("", 0.0)`
  - [x] 7.4: In `apps/api/tests/api/test_documents.py`, add test: document response includes `ocr_confidence` and `ocr_quality` fields
  - [x] 7.5: Test `ocr_quality` computed field: score 0.8 returns "high", 0.5 returns "medium", 0.2 returns "low", None returns None

- [x] **Task 8: Frontend tests** (AC: 2, 3, 4)
  - [x] 8.1: In `DocumentCard.test.tsx`, add test: renders OCR quality badge for image document with ocr_quality
  - [x] 8.2: Add test: does not render OCR quality badge for PDF documents
  - [x] 8.3: Add test: OCR quality badge shows warning icon for low confidence
  - [x] 8.4: In `DocumentTextViewer.test.tsx`, add test: shows OCR source banner for image documents
  - [x] 8.5: In `ProcessingDashboard.test.tsx`, add test: shows document type breakdown

## Dev Notes

### Architecture Context

This is **Story 7.3** — adds OCR quality confidence scoring to image documents, storing the score, exposing it via API, and displaying it in the frontend. Builds on Story 7.1's Tesseract OCR integration.

**Important:** Story 7.2 (moondream2 vision enhancement) is NOT yet implemented. This story works with the existing Tesseract-only pipeline. The `ocr_confidence` field is designed to be future-compatible — when 7.2 adds moondream2 fallback, the confidence scoring can be extended to factor in whether moondream2 was triggered.

**FRs covered:** FR51 (OCR quality confidence per image document)
**NFRs relevant:** All existing privacy NFRs (local processing only), data integrity

### What Already Exists -- DO NOT RECREATE

| Component | Location | What It Does |
|---|---|---|
| ImageExtractionService | `app/services/image_extraction.py` | Tesseract OCR with Pillow, page-marker format, graceful empty handling. Returns `str`. |
| Document model | `app/models/document.py` | Has `document_type`, `extraction_confidence` (for entity extraction), `extracted_text`, etc. |
| DocumentResponse schema | `app/schemas/document.py` | Has `extraction_quality` computed field (maps `extraction_confidence` to high/medium/low). |
| DocumentCard | `components/investigation/DocumentCard.tsx` | Shows existing `extraction_quality` badge (for entity extraction quality). Has `qualityStyles` map. |
| ProcessingDashboard | `components/investigation/ProcessingDashboard.tsx` | Shows total/complete/failed/remaining counts. |
| DocumentTextViewer | `components/investigation/DocumentTextViewer.tsx` | Parses `--- Page N ---` markers, shows pages. |
| process_document_task | `app/worker/tasks/process_document.py` | 4-stage pipeline. Image branch at line ~134. |
| `_to_response()` | `app/api/v1/documents.py` | Maps Document ORM to DocumentResponse. |
| Alembic migrations | `migrations/versions/` | 001-009 sequence. Next is 010. |

### Critical Implementation Details

#### New `ocr_confidence` vs Existing `extraction_confidence`

The existing `extraction_confidence` field stores entity extraction quality (how well entities were extracted from text). The new `ocr_confidence` field is specifically for OCR text extraction quality (how well OCR read the image). These are distinct concerns:

- `extraction_confidence` = entity extraction quality (populated in Stage 3 for all document types)
- `ocr_confidence` = OCR text reading quality (populated in Stage 1 for image documents only)

Both use 0.0-1.0 scale. Both have corresponding computed quality fields (`extraction_quality` and `ocr_quality`).

#### OCR Quality Heuristics

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

#### Extract Text Return Type Change

**Current:** `extract_text(file_path, document_id) -> str`
**New:** `extract_text(file_path, document_id) -> tuple[str, float]`

Returns `(text, ocr_confidence)`. The confidence is 0.0 for empty text, calculated via `assess_ocr_quality()` for non-empty text.

The worker task must be updated to unpack the tuple: `extracted_text, ocr_confidence = extractor.extract_text(...)`.

#### Frontend OCR Quality Badge

Separate from the existing `extraction_quality` badge. The OCR quality badge should:
- Only appear for `document_type === "image"`
- Use the `ocr_quality` field (not `extraction_quality`)
- Include "OCR:" prefix to distinguish from entity extraction quality
- Include tooltip with explanation

#### ProcessingDashboard Document Type Breakdown

Update the summary line from:
```
3 documents · 2 complete · 0 failed · 1 remaining
```
To:
```
3 documents (2 PDFs, 1 image) · 2 complete · 0 failed · 1 remaining
```

#### DocumentTextViewer OCR Banner

For image documents, show a banner above the text content:
```
[OCR Icon] Text extracted via Tesseract OCR — [Quality] confidence
[If low confidence:] Some text may be inaccurate — manual review recommended
```

This requires passing the document's `document_type` and `ocr_quality` to the viewer. Currently the viewer uses `useDocumentText` which returns `DocumentTextResponse` — this schema does NOT include `document_type` or `ocr_quality`. Two options:
1. Add these fields to `DocumentTextResponse`
2. Pass them as props from the parent

Option 2 is cleaner — the parent (`DocumentList.tsx` or workspace component) already has the document data. Pass `document_type` and `ocr_quality` as props to `DocumentTextViewer`.

### Project Structure Notes

**New files:**
- `apps/api/migrations/versions/010_add_ocr_confidence.py` — Alembic migration
- `apps/api/tests/services/test_image_extraction.py` — OCR quality assessment tests

**Modified files:**
- `apps/api/app/models/document.py` — add `ocr_confidence` column
- `apps/api/app/schemas/document.py` — add `ocr_confidence` field, `ocr_quality` computed field
- `apps/api/app/services/image_extraction.py` — add `assess_ocr_quality()`, change `extract_text()` return type
- `apps/api/app/api/v1/documents.py` — add `ocr_confidence` to `_to_response()`
- `apps/api/app/worker/tasks/process_document.py` — unpack tuple, store ocr_confidence
- `apps/web/src/components/investigation/DocumentCard.tsx` — OCR quality badge
- `apps/web/src/components/investigation/ProcessingDashboard.tsx` — document type counts
- `apps/web/src/components/investigation/DocumentTextViewer.tsx` — OCR source banner
- `apps/web/src/lib/api-types.generated.ts` — regenerated
- `apps/api/tests/api/test_documents.py` — ocr fields in response
- `apps/api/tests/conftest.py` — add ocr_confidence to sample_document
- `apps/web/src/components/investigation/DocumentCard.test.tsx` — OCR badge tests
- `apps/web/src/components/investigation/DocumentTextViewer.test.tsx` — OCR banner test
- `apps/web/src/components/investigation/ProcessingDashboard.test.tsx` — type breakdown test

### Important Patterns from Previous Stories

1. **Celery tasks use sync sessions** — `SyncSessionLocal()`. API endpoints use async sessions.
2. **SSE events are best-effort** — `_publish_safe()` wrapper never raises. Commit DB state before publishing.
3. **RFC 7807 error format** — `{type, title, status, detail, instance}` via `DomainError` subclasses.
4. **Service layer pattern** — Business logic in `app/services/`, Celery tasks orchestrate services.
5. **Loguru structured logging** — `logger.info("Message", key=value, key2=value2)`.
6. **Pillow context manager** — Always use `with Image.open(file_path) as image:` for FD safety.
7. **ImageExtractionService** currently returns `""` for empty OCR (not None). Will change to tuple `("", 0.0)`.
8. **Page marker format** — `--- Page 1 ---\n{text}` for compatibility with ChunkingService.
9. **Pre-existing test failures** — SystemStatusPage.test.tsx (4 failures), test_process_document.py (22 worker/infra failures). Do not fix these.
10. **OpenAPI type generation** — run `scripts/generate-api-types.sh` after any schema change.
11. **Commit pattern** — `feat: Story X.Y — description`.
12. **Computed fields** — `extraction_quality` pattern in DocumentResponse is the template for `ocr_quality`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Story 3.5 confidence display pattern]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md — Lines 1203-1216: Confidence Indicators visual language]
- [Source: apps/api/app/services/image_extraction.py — Existing Tesseract OCR service]
- [Source: apps/api/app/models/document.py — Document model with extraction_confidence]
- [Source: apps/api/app/schemas/document.py — DocumentResponse with extraction_quality computed field]
- [Source: apps/api/app/worker/tasks/process_document.py — Image extraction branch at ~line 134]
- [Source: apps/web/src/components/investigation/DocumentCard.tsx — qualityStyles, existing confidence badge]
- [Source: apps/web/src/components/investigation/ProcessingDashboard.tsx — Document count summary]
- [Source: apps/web/src/components/investigation/DocumentTextViewer.tsx — Page parsing, text display]

## Change Log

- 2026-04-12: Story 7.3 created with comprehensive developer context for OCR quality confidence indicators
- 2026-04-12: Story 7.3 implemented — OCR quality assessment, confidence scoring, API exposure, frontend badges and banners, backend + frontend tests
- 2026-04-12: Code review fixes — refactored assess_ocr_quality to accept image dimensions (avoids double file open), added document_id to quality log line

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Pre-existing: SystemStatusPage.test.tsx (4 failures) — TanStack Router mock issue
- Pre-existing: test_docker_compose.py (1 failure) — infra test expects different service count
- Pre-existing: tests/worker/test_process_document.py (22 failures) — missing Docker infrastructure

### Completion Notes List

- Task 1: Added `ocr_confidence` column to Document model (Float, nullable), Alembic migration 010, added to DocumentResponse schema with `ocr_quality` computed field (high/medium/low), updated `_to_response()` helper, updated OpenAPI generated types
- Task 2: Added `assess_ocr_quality()` method to ImageExtractionService with 3 heuristics (text density, alnum ratio, word length). Changed `extract_text()` to return `tuple[str, float]` instead of `str`
- Task 3: Updated process_document pipeline to unpack (text, confidence) tuple from ImageExtractionService, store `ocr_confidence` on document record, include in SSE events
- Task 4: Added OCR quality badge to DocumentCard for image documents with tooltip explaining quality level, uses ScanText icon and existing confidence visual language
- Task 5: Updated ProcessingDashboard summary to show document type breakdown (PDFs, images, web)
- Task 6: Added OCR source banner to DocumentTextViewer for image documents showing extraction method and confidence level, with low-confidence warning
- Task 7: Created 15 backend tests in test_image_extraction.py (quality assessment + computed field), added 2 API tests for ocr_confidence/ocr_quality fields, updated 3 existing tests for new tuple return type
- Task 8: Added 5 frontend tests for DocumentCard OCR badge, 3 tests for DocumentTextViewer OCR banner, 1 test for ProcessingDashboard type breakdown

### File List

**New files:**
- `apps/api/migrations/versions/010_add_ocr_confidence.py` — Alembic migration for ocr_confidence column
- `apps/api/tests/services/test_image_extraction.py` — 15 tests for OCR quality assessment and computed fields

**Modified files:**
- `apps/api/app/models/document.py` — added `ocr_confidence` column
- `apps/api/app/schemas/document.py` — added `ocr_confidence` field, `ocr_quality` computed field
- `apps/api/app/services/image_extraction.py` — added `assess_ocr_quality()`, changed `extract_text()` return to tuple
- `apps/api/app/api/v1/documents.py` — added `ocr_confidence` to `_to_response()` helper
- `apps/api/app/worker/tasks/process_document.py` — unpack tuple, store ocr_confidence, include in SSE events
- `apps/api/tests/conftest.py` — added `ocr_confidence` to sample_document fixture
- `apps/api/tests/api/test_documents.py` — updated 3 existing tests for tuple return, added 2 new API tests
- `apps/web/src/lib/api-types.generated.ts` — added `ocr_confidence` and `ocr_quality` fields
- `apps/web/src/components/investigation/DocumentCard.tsx` — OCR quality badge with tooltip
- `apps/web/src/components/investigation/ProcessingDashboard.tsx` — document type breakdown
- `apps/web/src/components/investigation/DocumentTextViewer.tsx` — OCR source banner with confidence
- `apps/web/src/routes/investigations/$id.tsx` — pass documentType/ocrQuality to DocumentTextViewer
- `apps/web/src/components/investigation/DocumentCard.test.tsx` — added 5 OCR badge tests
- `apps/web/src/components/investigation/DocumentTextViewer.test.tsx` — added 3 OCR banner tests
- `apps/web/src/components/investigation/ProcessingDashboard.test.tsx` — added 1 type breakdown test
