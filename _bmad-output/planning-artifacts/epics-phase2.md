---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
workflow_completed: true
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/ux-design-specification.md'
---

# OSINT - Epic Breakdown (Phase 2 — v1.1: Input Expansion & Polish)

## Overview

This document provides the epic and story breakdown for OSINT Phase 2 (v1.1), covering Input Expansion & Polish features deferred from MVP. These epics build on the foundation established by the 6 MVP epics and extend the platform with image OCR, manual entity management, web page ingestion, cross-investigation entity linking, and entity disambiguation.

## Requirements Inventory

### Functional Requirements

**Image OCR (4)**
- FR48: Investigator can upload image files (JPEG, PNG, TIFF) alongside PDFs to an investigation
- FR49: System extracts text from image files using Tesseract OCR
- FR50: System uses moondream2 (via Ollama) for enhanced image understanding and text extraction from complex/degraded layouts
- FR51: System indicates OCR quality confidence per image document (clean scan vs. degraded/handwritten)

**Manual Entity Management (4)**
- FR52: Investigator can manually create a new entity (person, organization, or location) with custom properties and a source annotation
- FR53: Investigator can edit/correct an entity's name and properties
- FR54: Investigator can merge two or more duplicate entities into a single entity, preserving all relationships and source citations from both
- FR55: Investigator can manually create a relationship between two entities with a source annotation

**Web Page Ingestion (3)**
- FR56: Investigator can submit a URL to capture a web page as a document source within an investigation
- FR57: System downloads, converts (HTML → text), and stores the web page content immutably
- FR58: Captured web pages are processed through the same entity extraction and embedding pipeline as PDFs

**Cross-Investigation Entity Linking (3)**
- FR59: System identifies matching entities across different investigations by name, type, and contextual similarity
- FR60: Investigator can view cross-investigation entity matches — entities that appear in multiple investigations
- FR61: Investigator can query across investigations to find shared entities and relationship patterns

**Entity Disambiguation (3)**
- FR62: System detects potential duplicate entities within an investigation (e.g., "Dep. Mayor Horvat" vs. "Deputy Mayor Horvat") and surfaces merge candidates
- FR63: System scores merge candidates by confidence (exact match, fuzzy name match, contextual similarity)
- FR64: Investigator can review suggested merges and approve or reject each one

**Total: 17 Functional Requirements (FR48–FR64)**

### NonFunctional Requirements

- NFR31: OCR processing (Tesseract + moondream2) completes per image page in <60 seconds on minimum hardware (16GB RAM, 8GB VRAM)
- NFR32: Web page capture and conversion completes within 30 seconds for standard web pages
- NFR33: Cross-investigation entity queries return results within 15 seconds
- NFR34: Entity merge operations are atomic — all relationships and source citations transfer completely, or the merge is rolled back with zero data loss

**Total: 4 Non-Functional Requirements (NFR31–NFR34)**

### Additional Requirements

**From PRD — Privacy Model Change for Web Ingestion:**
- Web page capture is the first feature introducing outbound network calls. These are opt-in per action (user explicitly submits a URL). The system never makes automatic/background outbound calls. NFR14 (zero outbound calls) is maintained for all other operations.

**From Architecture — Existing Infrastructure Support:**
- Single Qdrant collection with `investigation_id` payload filter was designed to enable cross-investigation search — no schema change needed for FR59–FR61
- New Ollama model required: `moondream2` for image understanding (alongside existing qwen3.5:9b and qwen3-embedding:8b)
- New API endpoints needed: entity CRUD (`POST/PATCH /entities/`), entity merge (`POST /entities/merge`), web capture (`POST /documents/capture`)
- Existing pipeline architecture (Celery + Redis + SSE) extends to support image and web page processing with minimal changes

**From UX — Journey 2 (Maria Edge Case):**
- Manual entity management (FR52–FR55) directly addresses Maria's workaround for bad OCR: manually add entities and relationships, correct names, merge duplicates
- Entity merge UI should show side-by-side comparison of entities being merged with all their relationships and sources before confirmation
- OCR quality indicators should follow the same confidence visual language (border thickness, badges) established in MVP

**From PRD — Innovation Risk Mitigation:**
- Context-based entity disambiguation + confidence scoring — maps to FR62–FR64
- Cross-investigation false positives — entity disambiguation should prevent false cross-investigation links

**From Architecture — Deferred Decisions Now Needed:**
- Neo4j full-text indexes and fuzzy matching capabilities required for entity disambiguation
- Entity merge requires cross-database transaction support: Neo4j (relationships), Qdrant (embeddings pointing to merged entity), and PostgreSQL (metadata)
- Document storage must extend to support image files and web page snapshots alongside existing PDF storage pattern

### FR Coverage Map

- FR48: Epic 7 — Upload image files alongside PDFs
- FR49: Epic 7 — Tesseract OCR text extraction from images
- FR50: Epic 7 — moondream2 enhanced image understanding
- FR51: Epic 7 — OCR quality confidence per image document
- FR52: Epic 8 — Manual entity creation
- FR53: Epic 8 — Entity name/property editing
- FR54: Epic 8 — Entity merge (preserving relationships + citations)
- FR55: Epic 8 — Manual relationship creation
- FR56: Epic 9 — URL submission for web page capture
- FR57: Epic 9 — Web page download, convert, store
- FR58: Epic 9 — Web pages through extraction pipeline
- FR59: Epic 10 — Cross-investigation entity matching
- FR60: Epic 10 — View cross-investigation entity matches
- FR61: Epic 10 — Cross-investigation entity queries
- FR62: Epic 8 — Duplicate entity detection within investigation
- FR63: Epic 8 — Merge candidate confidence scoring
- FR64: Epic 8 — Review and approve/reject merge suggestions

## Epic List

### Epic 7: Image Document Processing (OCR)
Investigator can upload image files (scanned documents, photos of records, screenshots) alongside PDFs, and the system extracts text via Tesseract OCR with moondream2 for complex layouts — extending investigations to documents that aren't born-digital. OCR quality confidence indicators tell the investigator which image documents to trust and which to review manually.

**FRs covered:** FR48, FR49, FR50, FR51

### Epic 8: Manual Entity Curation & Disambiguation
Investigator can create, edit, and merge entities manually, and the system proactively suggests duplicate entities for merging (e.g., "Dep. Mayor Horvat" and "Deputy Mayor Horvat"). This gives investigators direct control over the knowledge graph — fixing extraction errors, adding entities found through manual reading, and consolidating duplicates.

**FRs covered:** FR52, FR53, FR54, FR55, FR62, FR63, FR64

### Epic 9: Web Page Ingestion
Investigator can submit URLs to capture web pages as investigation documents — company registries, news articles, public filings, social media profiles. Captured pages are stored immutably and processed through the same entity extraction pipeline. This is the first feature introducing controlled outbound network calls (user-initiated only, opt-in per action).

**FRs covered:** FR56, FR57, FR58

### Epic 10: Cross-Investigation Intelligence
Investigator can discover that entities appearing in one investigation also appear in others — building a cumulative intelligence picture across separate cases. The system identifies cross-investigation matches by name, type, and contextual similarity, and the investigator can query across investigations to find shared entities and relationship patterns.

**FRs covered:** FR59, FR60, FR61

---

## Epic 7: Image Document Processing (OCR)

Investigator can upload image files (scanned documents, photos of records, screenshots) alongside PDFs, and the system extracts text via Tesseract OCR with moondream2 for complex layouts — extending investigations to documents that aren't born-digital. OCR quality confidence indicators tell the investigator which image documents to trust and which to review manually.

### Story 7.1: Image Upload & Tesseract OCR Text Extraction

As an investigator,
I want to upload image files (JPEG, PNG, TIFF) to my investigation and have text extracted automatically via OCR,
So that I can include scanned documents and photographs in my investigation alongside PDFs.

**Acceptance Criteria:**

**Given** the investigator is in an investigation workspace
**When** they drag and drop or select image files (JPEG, PNG, TIFF) alongside PDFs
**Then** image files are validated (accepted MIME types: image/jpeg, image/png, image/tiff)
**And** each image is stored immutably at `storage/{investigation_id}/{document_id}.{ext}` with SHA-256 checksum
**And** a document record is created in PostgreSQL with `document_type` field distinguishing "pdf" from "image"

**Given** an image document is queued for processing
**When** the Celery worker picks up the job
**Then** the pipeline detects the document type is "image" and routes to Tesseract OCR instead of PyMuPDF
**And** Tesseract extracts text from the image
**And** extracted text is stored as derived data, following the same chunking and provenance pattern as PDF text
**And** the document proceeds through the existing entity extraction and embedding pipeline

**Given** Tesseract OCR produces no text (blank image, non-text image)
**When** extraction completes with empty output
**Then** the document is marked as complete with zero entities and a "no text extracted" indicator
**And** the document is not marked as failed — empty OCR output is a valid result

**Given** an unsupported image format is uploaded
**When** the file middleware validates the upload
**Then** the upload is rejected with an RFC 7807 error: "Unsupported file type. Accepted: PDF, JPEG, PNG, TIFF"

### Story 7.2: moondream2 Enhanced Image Understanding

As an investigator,
I want the system to use visual AI understanding for images where basic OCR struggles,
So that I can extract useful text from handwritten notes, complex layouts, and degraded scans.

**Acceptance Criteria:**

**Given** the Docker Compose configuration
**When** the system starts up
**Then** moondream2 is available via Ollama alongside qwen3.5:9b and qwen3-embedding:8b
**And** the health endpoint reports moondream2 readiness status

**Given** Tesseract OCR produces output for an image document
**When** the OCR output quality is below a configurable threshold (e.g., low character confidence, very short output relative to image size)
**Then** the system routes the image to moondream2 for enhanced understanding
**And** moondream2 analyzes the image visually and extracts text/descriptions of content
**And** the moondream2 output supplements or replaces the Tesseract output

**Given** moondream2 processes an image with handwritten text
**When** it extracts content
**Then** the extracted text includes both recognized text and visual descriptions of content the model identifies
**And** the output clearly distinguishes OCR-extracted text from visual description

**Given** moondream2 is unavailable (Ollama down or model not loaded)
**When** an image would normally be routed to moondream2
**Then** the system falls back to Tesseract-only output
**And** the document is not marked as failed — degraded OCR is preferable to no processing
**And** a warning is logged via Loguru

**Given** image OCR processing runs on minimum hardware
**When** a single image page is processed (Tesseract + moondream2 if triggered)
**Then** total OCR processing completes in <60 seconds per image page (NFR31)

### Story 7.3: OCR Quality Confidence Indicators

As an investigator,
I want to see how well the system processed each image document,
So that I know which scans to trust and which ones I should manually review.

**Acceptance Criteria:**

**Given** an image document has been processed through OCR
**When** OCR completes (Tesseract alone or Tesseract + moondream2)
**Then** an OCR quality confidence score (0.0–1.0) is computed and stored with the document record
**And** the score factors in: Tesseract character-level confidence, text density relative to image area, and whether moondream2 fallback was triggered

**Given** the investigator views the document list
**When** image documents are present
**Then** each image document shows an OCR quality badge following the existing confidence visual language: high (solid border), medium (dashed), low (dotted + warning icon)
**And** the badge tooltip explains the quality level (e.g., "Low: handwritten content detected, moondream2 fallback used")

**Given** the processing dashboard shows real-time progress
**When** an image document completes processing
**Then** the document status card shows the OCR quality indicator
**And** the overall investigation summary distinguishes PDF documents from image documents in the count

**Given** the investigator clicks "View Text" on an image document
**When** the extracted text is displayed
**Then** the viewer indicates whether the text came from Tesseract, moondream2, or both
**And** low-confidence passages are visually flagged so the investigator knows where to focus manual review

---

## Epic 8: Manual Entity Curation & Disambiguation

Investigator can create, edit, and merge entities manually, and the system proactively suggests duplicate entities for merging (e.g., "Dep. Mayor Horvat" and "Deputy Mayor Horvat"). This gives investigators direct control over the knowledge graph — fixing extraction errors, adding entities found through manual reading, and consolidating duplicates.

### Story 8.1: Manual Entity Creation & Editing

As an investigator,
I want to manually create new entities and edit existing ones in my knowledge graph,
So that I can add information I found through manual reading and correct extraction errors.

**Acceptance Criteria:**

**Given** the investigator is viewing the graph or entity list
**When** they click "Add Entity"
**Then** a form presents fields for: name, type (person/organization/location), and optional properties
**And** the investigator can add a source annotation (free text describing where the information came from)
**And** the entity is created in Neo4j with `source="manual"` to distinguish it from LLM-extracted entities
**And** the new entity appears in the graph immediately

**Given** the API receives `POST /api/v1/investigations/{id}/entities/`
**When** the request contains a valid entity with name, type, and optional properties
**Then** the entity is persisted in Neo4j with a UUID, `confidence_score=1.0` (manually created = high confidence), and `investigation_id`
**And** if a source annotation is provided, it's stored as a property on the entity node
**And** the response follows the existing entity schema

**Given** the investigator views an Entity Detail Card (from MVP)
**When** they click "Edit" on the entity
**Then** they can modify the entity name and properties
**And** changes are persisted via `PATCH /api/v1/investigations/{id}/entities/{entity_id}`
**And** edit history is preserved (previous name stored as `aliases` property on the entity)
**And** the graph updates immediately to reflect the new name

**Given** the investigator edits an entity that has relationships and citations
**When** the name is changed
**Then** all existing relationships remain intact — only the entity name/properties change
**And** source citations and provenance chains are not affected

### Story 8.2: Manual Relationship Creation

As an investigator,
I want to manually draw connections between entities I know are related,
So that I can capture relationships I discovered through my own analysis that the system didn't detect.

**Acceptance Criteria:**

**Given** the investigator is viewing the graph with two or more entities visible
**When** they initiate "Add Relationship" (via Entity Detail Card action or graph context menu)
**Then** they can select a source entity, target entity, and relationship type (WORKS_FOR, KNOWS, LOCATED_AT, MENTIONED_IN, or custom)
**And** they can add a source annotation describing the evidence for this relationship
**And** the relationship is created in Neo4j with `source="manual"` and `confidence_score=1.0`

**Given** the API receives `POST /api/v1/investigations/{id}/relationships/`
**When** the request contains source_entity_id, target_entity_id, type, and optional annotation
**Then** the relationship is persisted in Neo4j connecting the two entity nodes
**And** the response includes the relationship ID, type, and connected entity names

**Given** a manual relationship is created
**When** the graph renders
**Then** the new edge appears with the same visual styling as LLM-extracted relationships
**And** the edge is distinguishable as manually created via a subtle indicator (e.g., "manual" badge on edge detail)
**And** clicking the edge shows the source annotation instead of a document citation

**Given** the investigator tries to create a duplicate relationship (same source, target, and type)
**When** the API validates the request
**Then** the existing relationship is returned with a note that it already exists
**And** no duplicate edge is created

### Story 8.3: Entity Merge with Relationship Preservation

As an investigator,
I want to merge duplicate entities into one, keeping all relationships and citations from both,
So that "Dep. Mayor Horvat" and "Deputy Mayor Horvat" become a single node with the full picture.

**Acceptance Criteria:**

**Given** the investigator identifies two entities that are the same real-world entity
**When** they select "Merge" from the Entity Detail Card and choose the target entity to merge into
**Then** a merge preview shows: both entity names, all relationships from both, all source citations from both
**And** the investigator selects which name to keep as primary (the other becomes an alias)
**And** they confirm the merge

**Given** the investigator confirms a merge
**When** `POST /api/v1/investigations/{id}/entities/merge` is called with `source_entity_id` and `target_entity_id`
**Then** all relationships from the source entity are transferred to the target entity
**And** all source citations and provenance chains from the source entity are added to the target entity
**And** the source entity's name is added to the target entity's `aliases` array
**And** the source entity node is deleted from Neo4j
**And** any Qdrant embeddings referencing the source entity are updated to reference the target entity
**And** the operation is atomic — all transfers complete or the entire merge is rolled back (NFR34)

**Given** both entities have a relationship to the same third entity of the same type
**When** the merge executes
**Then** duplicate relationships are consolidated into one, combining source citations from both
**And** the confidence score of the consolidated relationship reflects the combined evidence

**Given** the merge completes
**When** the graph re-renders
**Then** the merged entity appears as a single node with all combined relationships
**And** the node reflects the updated relationship count
**And** an SSE event notifies the frontend of the entity change

### Story 8.4: Automated Duplicate Entity Detection & Merge Suggestions

As an investigator,
I want the system to detect potential duplicate entities and suggest merges,
So that I don't have to manually scan hundreds of entities to find duplicates.

**Acceptance Criteria:**

**Given** an investigation has entities in Neo4j
**When** the investigator opens a "Review Duplicates" panel (accessible from the graph toolbar or entity list)
**Then** the system queries for potential duplicate entities using: exact name match (case-insensitive), fuzzy name match (Levenshtein distance), and contextual similarity (same type, overlapping source documents)
**And** results are presented as merge candidate pairs, ranked by confidence score (FR63)

**Given** Neo4j contains entities for disambiguation
**When** the duplicate detection query runs
**Then** Neo4j full-text indexes are used for efficient fuzzy matching
**And** only entities within the same investigation are compared (no cross-investigation matching in this story)
**And** each candidate pair shows: both entity names, match type (exact/fuzzy/contextual), confidence score, and relationship count for each

**Given** the investigator reviews a merge suggestion
**When** they click "Review" on a candidate pair
**Then** a side-by-side comparison shows both entities with all their relationships and source documents
**And** the investigator can approve the merge (executes Story 8.3 merge flow) or reject it
**And** rejected suggestions are remembered and not shown again for the same pair

**Given** new entities are extracted from a newly uploaded document
**When** extraction completes
**Then** the system runs duplicate detection against existing entities for the newly extracted ones
**And** if new merge candidates are found, a notification badge appears on the "Review Duplicates" panel
**And** the investigator is not interrupted — suggestions are passive, not modal

---

## Epic 9: Web Page Ingestion

Investigator can submit URLs to capture web pages as investigation documents — company registries, news articles, public filings, social media profiles. Captured pages are stored immutably and processed through the same entity extraction pipeline. This is the first feature introducing controlled outbound network calls (user-initiated only, opt-in per action).

### Story 9.1: Web Page Capture & Storage

As an investigator,
I want to submit a URL and have the web page captured as a document in my investigation,
So that I can include online sources like company registries, news articles, and public filings alongside my uploaded files.

**Acceptance Criteria:**

**Given** the investigator is in an investigation workspace
**When** they click "Capture Web Page" and enter a URL
**Then** the system validates the URL format
**And** a document record is created in PostgreSQL with `document_type="web"`, the source URL, and status "queued"
**And** the capture job is queued via Celery

**Given** a web capture job is picked up by the Celery worker
**When** the worker fetches the URL
**Then** the full HTML content is downloaded and stored immutably at `storage/{investigation_id}/{document_id}.html`
**And** the HTML is converted to clean text (stripped of scripts, styles, navigation — preserving article content and structure)
**And** a SHA-256 checksum of the original HTML is computed and stored
**And** page metadata is extracted and stored: title, URL, capture timestamp
**And** capture completes within 30 seconds for standard web pages (NFR32)

**Given** the URL is unreachable (timeout, DNS failure, 404)
**When** the capture fails
**Then** the document status is set to "failed" with a clear error: "Could not reach URL: [reason]"
**And** a `document.failed` SSE event is published
**And** the investigator can retry or enter a different URL

**Given** the system is operating normally on other features
**When** no web capture is in progress
**Then** zero outbound network calls are made — web capture is the only feature that makes outbound requests
**And** outbound requests occur only when the investigator explicitly submits a URL (opt-in per action)

**Given** the investigator views the document list
**When** web-captured documents are present
**Then** each web document shows: page title, source URL, capture date, and processing status
**And** web documents are visually distinguished from PDFs and images (e.g., globe icon instead of document icon)

### Story 9.2: Web Document Processing & Entity Extraction

As an investigator,
I want captured web pages to go through the same entity extraction and embedding pipeline as my other documents,
So that entities from online sources are part of my knowledge graph and searchable alongside everything else.

**Acceptance Criteria:**

**Given** a web page has been captured and text extracted (Story 9.1)
**When** the Celery worker continues processing
**Then** the extracted text is chunked following the same strategy as PDF documents
**And** each chunk records its source as the web document with URL and capture timestamp as provenance
**And** the document proceeds through entity extraction (qwen3.5:9b) and embedding generation (qwen3-embedding:8b)
**And** SSE events track progress through the same stages: extracting_entities → embedding → complete

**Given** entities are extracted from a web document
**When** they are stored in Neo4j
**Then** entities follow the same schema as PDF-extracted entities (name, type, confidence_score, investigation_id)
**And** provenance chains link back to the web document with URL metadata
**And** if an extracted entity matches an existing entity in the investigation, the existing entity is reused and the web document is added as an additional source

**Given** the investigator asks a question via Q&A
**When** the answer includes facts from a web-captured document
**Then** citations display the page title and URL instead of a filename and page number
**And** clicking the citation opens the Citation Modal showing the relevant passage from the captured page
**And** the citation clearly indicates this is from a web source

**Given** the investigator views the graph after web documents are processed
**When** entities from web and non-web documents are both present
**Then** entities sourced exclusively from web documents are visually indistinguishable from other entities (same node styling)
**And** the document filter in Graph Controls includes web documents alongside PDFs and images

---

## Epic 10: Cross-Investigation Intelligence

Investigator can discover that entities appearing in one investigation also appear in others — building a cumulative intelligence picture across separate cases. The system identifies cross-investigation matches by name, type, and contextual similarity, and the investigator can query across investigations to find shared entities and relationship patterns.

### Story 10.1: Cross-Investigation Entity Matching Engine

As an investigator,
I want the system to automatically detect when entities in my investigation match entities in my other investigations,
So that I discover unexpected connections between cases I'm working on.

**Acceptance Criteria:**

**Given** an investigation has completed entity extraction
**When** the investigator opens a "Cross-Investigation Links" panel (accessible from the graph toolbar or investigation header)
**Then** the system queries across all investigations for matching entities by name (case-insensitive exact match), type, and contextual similarity (overlapping aliases, similar relationship patterns)
**And** matches are returned within 15 seconds (NFR33)

**Given** the Qdrant collection stores all embeddings with `investigation_id` as a payload field
**When** the cross-investigation matching runs
**Then** the system leverages the existing single-collection architecture — no schema changes needed
**And** Neo4j queries use entity name + type matching across all investigations the user has
**And** Qdrant vector similarity can supplement name matching to find entities with similar contextual descriptions

**Given** a match is found between Investigation A and Investigation B
**When** the results are presented
**Then** each match shows: entity name, type, the investigations it appears in, relationship count per investigation, and a match confidence score
**And** matches are ranked by confidence (exact name match > fuzzy match > contextual similarity)

**Given** new entities are extracted in any investigation
**When** extraction completes
**Then** the system runs cross-investigation matching for the newly extracted entities in the background
**And** if new cross-investigation matches are found, a notification badge appears on the "Cross-Investigation Links" panel
**And** no blocking or interruption occurs — matching is passive and background

**Given** the investigator has only one investigation
**When** they access the Cross-Investigation Links panel
**Then** a clear message explains: "Cross-investigation matching requires two or more investigations. Create another investigation to discover shared entities."

### Story 10.2: Cross-Investigation Entity Exploration & Querying

As an investigator,
I want to explore entities that appear across multiple investigations and query for shared patterns,
So that I can build a cumulative intelligence picture and find connections I wouldn't see within a single case.

**Acceptance Criteria:**

**Given** cross-investigation entity matches exist (from Story 10.1)
**When** the investigator clicks on a matched entity in the Cross-Investigation Links panel
**Then** a detail view shows the entity's presence across investigations: name, type, relationships in each investigation, and source documents per investigation
**And** the investigator can see side-by-side how the entity connects to different networks in different cases

**Given** the investigator wants to query across investigations
**When** they use a "Cross-Investigation Search" input in the Cross-Investigation Links panel
**Then** they can search for an entity name, type, or keyword across all their investigations
**And** results show which investigations contain matching entities and the relationship context in each
**And** results are returned within 15 seconds (NFR33)

**Given** the investigator views a cross-investigation match
**When** they click "Open in Investigation" on a specific investigation
**Then** they navigate to that investigation's workspace with the matched entity centered and highlighted in the graph
**And** the Entity Detail Card opens for that entity showing its relationships within that investigation

**Given** a cross-investigation match is a false positive (different real-world entities with the same name)
**When** the investigator reviews the match
**Then** they can dismiss the match as "not the same entity"
**And** dismissed matches are remembered and not shown again
**And** dismissed matches do not affect the entity data in either investigation

**Given** the investigator views the investigation list (home page)
**When** investigations have cross-investigation entity matches
**Then** each investigation card shows a count of cross-investigation entity links (e.g., "3 entities shared with other investigations")
**And** this count serves as a discovery prompt to explore connections
