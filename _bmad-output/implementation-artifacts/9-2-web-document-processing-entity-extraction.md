# Story 9.2: Web Document Processing & Entity Extraction

Status: done

## Story

As an investigator,
I want captured web pages to go through the same entity extraction and embedding pipeline as my other documents,
So that entities from online sources are part of my knowledge graph and searchable alongside everything else.

## Acceptance Criteria

1. **Given** a web page has been captured and text extracted (Story 9.1) **When** the Celery worker continues processing **Then** the extracted text is chunked following the same strategy as PDF documents **And** each chunk records its source as the web document with URL and capture timestamp as provenance **And** the document proceeds through entity extraction (qwen3.5:9b) and embedding generation (qwen3-embedding:8b) **And** SSE events track progress through the same stages: extracting_entities → embedding → complete

2. **Given** entities are extracted from a web document **When** they are stored in Neo4j **Then** entities follow the same schema as PDF-extracted entities (name, type, confidence_score, investigation_id) **And** provenance chains link back to the web document with URL metadata **And** if an extracted entity matches an existing entity in the investigation, the existing entity is reused and the web document is added as an additional source

3. **Given** the investigator asks a question via Q&A **When** the answer includes facts from a web-captured document **Then** citations display the page title and URL instead of a filename and page number **And** clicking the citation opens the Citation Modal showing the relevant passage from the captured page **And** the citation clearly indicates this is from a web source

4. **Given** the investigator views the graph after web documents are processed **When** entities from web and non-web documents are both present **Then** entities sourced exclusively from web documents are visually indistinguishable from other entities (same node styling) **And** the document filter in Graph Controls includes web documents alongside PDFs and images

## Tasks / Subtasks

- [x] Task 1: Enhance Citation schema — add web-source metadata (AC: #3)
  - [x] 1.1 Add `source_url: str | None` and `document_type: str` fields to `Citation` in `app/schemas/query.py`
  - [x] 1.2 Update the frontend `Citation` interface in `apps/web/src/components/qa/types.ts` to match
  - [x] 1.3 Update `api-types.generated.ts` to reflect the new schema fields

- [x] Task 2: Enrich citation pipeline with web document metadata (AC: #3)
  - [x] 2.1 Update `_resolve_document_filenames` in `app/services/query.py` to also fetch `document_type` and `source_url` columns from the `documents` table
  - [x] 2.2 Update the citation builder loop in `_merge_results` to populate `source_url` and `document_type` on each `Citation` object
  - [x] 2.3 Update `_format_citation_list` to include URL when present (e.g., "[1] Page Title (web: https://...): excerpt")

- [x] Task 3: Update CitationModal to display web source info (AC: #3)
  - [x] 3.1 Update `CitationModal.tsx` — show page title + URL for web documents instead of just filename + page number
  - [x] 3.2 Add a clickable external link icon that opens the source URL in a new tab (for web citations only)
  - [x] 3.3 Add a "Web Source" badge/indicator in the modal header for web-type citations

- [x] Task 4: Ensure document filter includes web documents (AC: #4)
  - [x] 4.1 Verify `GraphFilterPanel.tsx` document dropdown already lists all document types (it uses the documents array from the investigation; web documents are included by default — confirm no filtering by document_type)
  - [x] 4.2 Add Globe icon prefix for web documents in the document filter dropdown options to visually distinguish them

- [x] Task 5: Backend tests — citation metadata for web documents (AC: #2, #3)
  - [x] 5.1 Add test in `tests/services/test_query.py` — `test_citations_include_web_metadata`: mock a web document with `source_url` and `document_type="web"`, verify citations contain the new fields
  - [x] 5.2 Add test in `tests/services/test_query.py` — `test_format_citation_list_with_web_source`: verify `_format_citation_list` includes URL for web citations

- [x] Task 6: Frontend tests — CitationModal web source display (AC: #3)
  - [x] 6.1 Add test in `CitationModal.test.tsx` — `test_citation_modal_shows_web_source_badge`: render modal with a web citation, verify web badge and URL appear
  - [x] 6.2 Add test in `CitationModal.test.tsx` — `test_citation_modal_external_link`: verify external URL link renders for web citations

- [x] Task 7: Frontend tests — GraphFilterPanel web document inclusion (AC: #4)
  - [x] 7.1 Add test in `GraphFilterPanel.test.tsx` — `test_document_filter_includes_web_documents`: render with mixed document types, verify web docs appear in dropdown

## Dev Notes

### What Already Works (Story 9.1 Baseline)

The existing pipeline from Story 9.1 **already processes web documents end-to-end**. The `process_document_task` in `app/worker/tasks/process_document.py` routes web documents through:
1. **Text extraction**: `web_capture.fetch_and_store()` fetches HTML, converts to text with `--- Page 1 ---` marker, stores in `extracted_text`
2. **Chunking**: `ChunkingService.chunk_document()` processes the extracted text — works identically for web and PDF documents since text is pre-formatted with page markers
3. **Entity extraction**: `EntityExtractionService.extract_from_chunks()` extracts entities via Ollama qwen3.5:9b — document type agnostic
4. **Embedding**: `EmbeddingService.embed_chunks()` generates embeddings via qwen3-embedding:8b — document type agnostic
5. **SSE events**: All stage transitions publish events — document type agnostic

**Key insight**: The processing pipeline is already type-agnostic. Web documents flow through chunking, entity extraction, and embedding identically to PDFs. The entity storage in Neo4j uses MERGE to reuse existing entities (matched by name + type + investigation_id). Provenance MENTIONED_IN edges link entities back to the Document node by `document_id`.

### What This Story Actually Needs

The story's ACs focus on **presentation layer changes** — how web-sourced citations and documents appear to the investigator:

1. **Citation display** (AC #3): When Q&A answers cite a web document, show the page title and URL instead of just filename + page number. The Citation Modal should clearly indicate web sources.
2. **Document filter** (AC #4): Web documents should appear in the graph's document filter dropdown alongside PDFs and images (they likely already do — verify).
3. **Entity parity** (AC #2, #4): Entities from web documents should be visually identical to those from other sources (already true — entity styling is type-based, not source-based).

### Citation Schema Enhancement

The `Citation` model in `app/schemas/query.py` currently has:
```python
class Citation(BaseModel):
    citation_number: int
    document_id: str
    document_filename: str
    chunk_id: str
    page_start: int
    page_end: int
    text_excerpt: str
```

Add two fields:
```python
    source_url: str | None = None
    document_type: str = "pdf"
```

The `_resolve_document_filenames` function (line 558 in `query.py`) currently only fetches `Document.id` and `Document.filename`. Extend it to also fetch `Document.document_type` and `Document.source_url`, and return a richer mapping.

### Citation Builder in _merge_results

In `_merge_results` (line 635), after resolving document filenames, the citation builder loop (line 705) creates `Citation` objects. Update it to populate the new fields:

```python
doc_meta = filename_map.get(source.get("document_id", ""), {})
citations.append(Citation(
    citation_number=i,
    document_id=source.get("document_id", ""),
    document_filename=doc_meta.get("filename", "unknown"),
    chunk_id=source.get("chunk_id", ""),
    page_start=source.get("page_start", 0) or 0,
    page_end=source.get("page_end", 0) or 0,
    text_excerpt=source.get("text_excerpt", ""),
    source_url=doc_meta.get("source_url"),
    document_type=doc_meta.get("document_type", "pdf"),
))
```

### Citation Format for LLM Context

Update `_format_citation_list` to include URL for web sources:
```python
def _format_citation_list(citations: list[Citation]) -> str:
    lines = []
    for c in citations:
        if c.source_url:
            lines.append(f"[{c.citation_number}] {c.document_filename} (web: {c.source_url}): {c.text_excerpt[:200]}")
        else:
            lines.append(f"[{c.citation_number}] {c.document_filename} (pages {c.page_start}-{c.page_end}): {c.text_excerpt[:200]}")
    return "\n".join(lines)
```

### Frontend CitationModal Changes

The `CitationModal.tsx` currently shows:
- Title: `Citation — {filename}`
- Description: `Page X` or `Pages X–Y`

For web documents, change to:
- Title: `Citation — {filename}` (filename is the page title for web docs)
- Description: Show URL with globe icon + "Web Source" badge
- Add external link button to open the URL in a new tab
- Keep the chunk context viewer as-is (works for any document type)

Detection: check `citation.document_type === "web"` (or `citation.source_url` presence).

### Frontend Citation Type Update

Add to the `Citation` interface in `types.ts`:
```typescript
export interface Citation {
  citation_number: number;
  document_id: string;
  document_filename: string;
  chunk_id: string;
  page_start: number;
  page_end: number;
  text_excerpt: string;
  source_url: string | null;
  document_type: string;
}
```

### GraphFilterPanel — Web Document Inclusion

The `GraphFilterPanel.tsx` document dropdown already lists all documents from the investigation via the `documents` prop. Since web documents are standard `Document` records with `document_type="web"`, they are already included. The only enhancement needed is adding a visual indicator (Globe icon prefix) to distinguish web documents in the dropdown.

### Entity Visual Parity (No Changes Needed)

Entity nodes in the graph are styled by entity type (Person/Organization/Location), not by source document type. The `cytoscape-styles.ts` applies colors based on entity type labels. Web-sourced entities are visually identical to PDF-sourced entities. No code changes required for AC #4 entity styling.

### Project Structure Notes

Files to modify:
- `apps/api/app/schemas/query.py` — add `source_url`, `document_type` to Citation
- `apps/api/app/services/query.py` — enrich `_resolve_document_filenames`, update citation builder, update `_format_citation_list`
- `apps/web/src/components/qa/types.ts` — add `source_url`, `document_type` to Citation interface
- `apps/web/src/components/qa/CitationModal.tsx` — web source display
- `apps/web/src/components/graph/GraphFilterPanel.tsx` — Globe icon for web docs in dropdown
- `apps/web/src/lib/api-types.generated.ts` — update generated types
- `apps/api/tests/services/test_query.py` — add web citation tests
- `apps/web/src/components/qa/CitationModal.test.tsx` — add web source display tests
- `apps/web/src/components/graph/GraphFilterPanel.test.tsx` — add web doc inclusion test

No new files needed. No new directories.

### References

- [Source: _bmad-output/implementation-artifacts/9-1-web-page-capture-storage.md — full Story 9.1 implementation details]
- [Source: apps/api/app/worker/tasks/process_document.py — web document routing (line 126)]
- [Source: apps/api/app/services/query.py — citation pipeline (_merge_results at line 635, _resolve_document_filenames at line 558)]
- [Source: apps/api/app/schemas/query.py — Citation model]
- [Source: apps/web/src/components/qa/CitationModal.tsx — current citation display]
- [Source: apps/web/src/components/graph/GraphFilterPanel.tsx — document filter dropdown (line 199)]
- [Source: apps/web/src/components/qa/types.ts — frontend Citation interface]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- All 7 tasks and subtasks completed
- 362 backend tests pass (excluding pre-existing docker compose and worker infrastructure failures), 0 regressions
- 268 frontend tests pass, 0 regressions (4 pre-existing SystemStatusPage failures unrelated to changes)
- Key finding: The processing pipeline (chunking, entity extraction, embedding) was already document-type-agnostic from Story 9.1, so no pipeline changes were needed
- This story focused entirely on presentation-layer enhancements: enriching citation metadata with web source info, updating the CitationModal to display web source badges/URLs, and ensuring the document filter includes web documents
- Added `source_url` and `document_type` fields to the `Citation` Pydantic model and frontend `Citation` interface
- Renamed `_resolve_document_filenames` to `_resolve_document_metadata` to reflect its expanded role
- CitationModal now shows Globe icon, "Web Source" badge, and clickable external URL link for web citations
- GraphFilterPanel document dropdown shows `[Web]` prefix for web documents

### File List

**Modified files:**
- apps/api/app/schemas/query.py — added `source_url`, `document_type` to Citation model
- apps/api/app/services/query.py — renamed `_resolve_document_filenames` to `_resolve_document_metadata`, enriched citation builder, updated `_format_citation_list` for web URLs
- apps/web/src/components/qa/types.ts — added `source_url`, `document_type` to Citation interface
- apps/web/src/components/qa/CitationModal.tsx — web source badge, URL display, external link icon, updated aria-label
- apps/web/src/components/qa/AnswerPanel.tsx — web-aware citation footer and aria-label (review fix)
- apps/web/src/components/graph/GraphFilterPanel.tsx — `[Web]` prefix for web documents in dropdown
- apps/api/tests/services/test_query.py — added 2 web citation metadata tests
- apps/web/src/components/qa/CitationModal.test.tsx — added 4 web source display tests
- apps/web/src/components/graph/GraphFilterPanel.test.tsx — added 1 web document inclusion test
- apps/web/src/components/qa/AnswerPanel.test.tsx — added Citation type fields (review fix)
- apps/web/src/routes/investigations/-$id.test.tsx — added Citation type fields to 4 fixtures (review fix)

### Senior Developer Review (AI)

**Date:** 2026-04-12
**Outcome:** Changes Requested -> Fixed

**Issues Found:** 0 Critical, 2 High, 1 Medium — all resolved.

**Action Items:**
- [x] [HIGH] AnswerPanel citation footer showed `, page X` for web documents — added conditional to show `(web)` for web-sourced citations instead of page numbers
- [x] [HIGH] TypeScript compile errors — Citation objects in 6 test files (`AnswerPanel.test.tsx`, `investigations/-$id.test.tsx` x4) missing new `source_url` and `document_type` fields. Added required fields to all test fixtures.
- [x] [MEDIUM] AnswerPanel superscript aria-label said `page X` for web sources — added conditional to say `(web)` instead

### Change Log

- 2026-04-12: Story 9.2 implemented — web document processing & entity extraction (all 7 tasks)
- 2026-04-12: Code review fixes — 3 issues resolved (2 HIGH, 1 MEDIUM)
