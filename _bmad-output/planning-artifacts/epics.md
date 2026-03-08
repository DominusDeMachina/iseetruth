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

# OSINT - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for OSINT, decomposing the requirements from the PRD, UX Design, and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

**Investigation Management (4)**
- FR1: Investigator can create a new investigation with a name and description
- FR2: Investigator can view a list of all their investigations
- FR3: Investigator can delete an investigation and all its associated data
- FR4: Investigator can open an investigation to view its documents, entities, and graph

**Document Ingestion (6)**
- FR5: Investigator can upload multiple PDF files simultaneously to an investigation
- FR6: Investigator can drag and drop a folder of PDFs into the upload area
- FR7: System extracts text content from uploaded PDF documents
- FR8: System stores original uploaded documents immutably (never modified)
- FR9: Investigator can view the list of documents in an investigation with processing status
- FR10: Investigator can view the extracted text of a processed document

**Entity Extraction & Knowledge Graph (6)**
- FR11: System automatically extracts people, organizations, and locations from document text using local LLM
- FR12: System automatically detects relationships between extracted entities (WORKS_FOR, KNOWS, LOCATED_AT, MENTIONED_IN)
- FR13: System stores extracted entities and relationships in a knowledge graph
- FR14: System assigns confidence scores to extracted entities and relationships
- FR15: System maintains provenance chain for every extracted fact (entity → chunk → document → page/passage)
- FR16: System generates vector embeddings for document chunks and stores them for semantic search

**Natural Language Query & Answer (6)**
- FR17: Investigator can ask natural language questions about their investigation
- FR18: System translates natural language queries into graph and vector search operations
- FR19: System returns answers grounded exclusively in knowledge graph data (GRAPH FIRST — no hallucinated facts)
- FR20: Every fact in an answer includes a source citation linking to the original document passage
- FR21: Investigator can click a citation to view the original source passage in context
- FR22: System reports "No connection found in your documents" when the graph cannot answer a question

**Graph Visualization (8)**
- FR23: Investigator can view an interactive graph of entities and relationships in their investigation
- FR24: System dynamically loads graph nodes on demand (no upper limit on graph size)
- FR25: Investigator can click a node to view an entity detail card with properties, relationships, and source documents
- FR26: Investigator can click an edge to view relationship details with source citation
- FR27: Investigator can expand a node's neighborhood by interacting with it (load connected entities)
- FR28: Investigator can filter the graph by entity type (people, organizations, locations)
- FR29: Investigator can filter the graph by source document
- FR30: Investigator can search for entities and see matching nodes highlighted in the graph

**Processing Pipeline & Feedback (4)**
- FR31: System processes uploaded documents asynchronously via a job queue
- FR32: Investigator receives real-time progress updates during document processing (per-document status)
- FR33: System displays per-document processing status (queued, extracting text, extracting entities, embedding, complete, failed)
- FR34: Investigator can view processing results as they arrive (entities appearing while other documents still process)

**Resilience & Error Handling (6)**
- FR35: System marks documents as "failed — retry available" when processing fails mid-extraction
- FR36: System automatically retries failed documents when the LLM service recovers
- FR37: Investigator can manually trigger retry for failed documents
- FR38: System preserves all successfully processed data when a service fails (no data loss from partial failures)
- FR39: System provides graph browsing and visualization when the LLM service is unavailable (degraded mode)
- FR40: System displays clear service status to the investigator (which services are operational)

**Deployment & Setup (4)**
- FR41: Administrator can deploy the complete system with a single Docker Compose command
- FR42: System provides health check endpoints for all services
- FR43: System detects and reports LLM model readiness before allowing queries
- FR44: System displays clear error messages when hardware requirements are insufficient

**Confidence & Transparency (3)**
- FR45: Investigator can view confidence indicators for each processed document (extraction quality)
- FR46: Investigator can view confidence scores for individual entities
- FR47: Investigator can inspect the evidence supporting any relationship (which documents, which passages)

**Total: 47 Functional Requirements**

### NonFunctional Requirements

**Performance — Document Processing Pipeline (4)**
- NFR1: 100-page PDF fully processed (text extraction + entity extraction + embedding) in <15 minutes on minimum hardware (16GB RAM, 8GB VRAM)
- NFR2: Individual document text extraction completes in <30 seconds per 100 pages
- NFR3: Processing pipeline handles bulk upload of 50+ documents without queue failure or memory exhaustion
- NFR4: Real-time progress updates (SSE) delivered to frontend within 1 second of processing state change

**Performance — Query & Response (3)**
- NFR5: Natural language question returns answer with citations in <30 seconds on minimum hardware
- NFR6: Graph path queries (shortest path between two entities) return in <10 seconds
- NFR7: Query streaming begins within 5 seconds (progressive response, not all-or-nothing)

**Performance — Frontend Responsiveness (6)**
- NFR8: Initial application load in <3 seconds
- NFR9: Graph visualization renders up to 500 visible nodes in <2 seconds
- NFR10: Node neighborhood expansion (click to load connected entities) completes in <1 second
- NFR11: Entity search returns results in <500 milliseconds
- NFR12: All performance targets measured against minimum spec: 16GB RAM, 8GB VRAM (RTX 3060/4060 or M1/M2 Mac with 16GB unified), 50GB SSD
- NFR13: UI interactions (navigation, graph browsing) respond in <500ms while document processing is active

**Security & Privacy (4)**
- NFR14: Zero outbound network connections during normal operation (document processing, querying, graph browsing)
- NFR15: All LLM inference executes locally via Ollama — no external API calls under any circumstances
- NFR16: No telemetry, analytics, crash reporting, or update checking that contacts external servers
- NFR17: System is fully operational on an air-gapped network (no internet required after initial setup and model download)

**Document Integrity (3)**
- NFR18: Original uploaded documents are stored byte-for-byte identical to the uploaded file (verified by checksum)
- NFR19: System never modifies, re-encodes, compresses, or alters source documents
- NFR20: Derived data (extracted text, entities, relationships, embeddings) is stored separately from source documents with clear provenance

**Grounding Guarantee (2)**
- NFR21: 100% of facts presented in query answers are traceable to a specific source document passage — zero tolerance for ungrounded assertions
- NFR22: System never presents LLM-generated speculation, inference, or "likely" connections as facts

**Reliability & Data Integrity (6)**
- NFR23: All investigation data (documents, entities, relationships, embeddings) persists across application restarts, Docker restarts, and system reboots
- NFR24: No data loss from partial processing failures — successfully processed documents remain intact when later documents fail
- NFR25: Database transactions are atomic — no partially-written entities or relationships
- NFR26: Individual service failure (Ollama, Neo4j, Qdrant) does not crash the entire application — degraded functionality rather than total failure
- NFR27: Application recovers automatically when failed services come back online without requiring full restart
- NFR28: Processing queue survives Ollama restarts — pending jobs resume, not lost

**Deployment Reliability (2)**
- NFR29: Docker Compose deployment succeeds on first attempt on supported platforms (Linux, macOS with Docker Desktop) with documented prerequisites
- NFR30: System provides clear, actionable error messages when deployment fails (insufficient memory, port conflicts, missing GPU drivers)

**Total: 30 Non-Functional Requirements**

### Additional Requirements

**From Architecture — Starter Template & Project Setup:**
- Architecture specifies starter templates: `create-vite` react-swc-ts (frontend) + `uv init` (backend). This defines Epic 1 Story 1.
- Monorepo structure: `apps/web` (React+Vite) + `apps/api` (FastAPI+Celery)
- Package managers: pnpm (frontend), uv (Python)

**From Architecture — Stack Revisions (supersede PRD):**
- React + Vite 7.x SPA instead of Next.js (no SSR/SSG needed for localhost app, saves memory)
- OpenAPI-generated types (openapi-typescript + openapi-fetch) instead of tRPC (tRPC requires TypeScript server, incompatible with FastAPI)
- Updated LLM models: qwen3.5:9b for extraction/query, qwen3-embedding:8b for embeddings (supersede PRD's Qwen 2.5 7B and nomic-embed-text)

**From Architecture — Data Layer:**
- SQLModel + Alembic for PostgreSQL ORM and migrations
- Single Qdrant collection with `investigation_id` payload filter (enables future cross-investigation search)
- Investigation-scoped document storage: `storage/{investigation_id}/{document_id}.pdf` with host bind mount
- UUID v4 for all entity IDs

**From Architecture — Infrastructure:**
- 7-service Docker Compose: app (FastAPI+Celery combined), web (Nginx), postgres, neo4j, qdrant, redis, ollama
- Redis AOF persistence for queue durability
- Bind mount for documents (visible on host), named volumes for databases
- Two compose files: `docker-compose.yml` (production) and `docker-compose.dev.yml` (infrastructure only)
- Development workflow: Docker for infrastructure, native Vite HMR + FastAPI auto-reload for apps

**From Architecture — API & Communication:**
- Resource-based REST with `/api/v1/` prefix (16 endpoints defined)
- RFC 7807 Problem Details for all error responses
- SSE via Redis pub/sub → FastAPI → browser (11 event types defined with dot-notation)
- CORS: localhost origins only (5173 dev, 80 prod)
- Pydantic + file middleware for input validation
- Type flow: Pydantic models → OpenAPI spec → TypeScript types → openapi-fetch

**From Architecture — Implementation Patterns:**
- Comprehensive naming conventions (22-row table covering Python, PostgreSQL, Neo4j, TypeScript, CSS, API, SSE, Qdrant)
- Loguru structured logging (stdout, JSON format available)
- Feature-grouped frontend components (graph/, qa/, citation/, investigation/, processing/, status/, layout/)
- Backend structure: api/ → schemas/ → models/ → services/ → worker/ → db/ → llm/
- Multi-database cascading delete order: Neo4j → Qdrant → filesystem → PostgreSQL (last for consistency)

**From Architecture — Deferred to Story-Level:**
- Document chunking strategy (page-based, paragraph-based, or fixed-size — to be decided during implementation)
- Neo4j schema constraints and indexes
- Qdrant collection configuration (vector dimensions, distance metric, HNSW parameters)
- Docker resource limits for 16GB hardware

**From UX — Visual Design:**
- Dark theme as default (investigation context, reduced eye strain)
- Color tokens via CSS custom properties for entity types and confidence indicators
- Typography: Source Serif 4 (editorial text) + Inter (UI text), self-hosted via @fontsource
- Animation patterns: graph expansion 400ms, highlighting 600ms, modals 150ms, toasts 200ms
- All animations respect `prefers-reduced-motion`

**From UX — Layout & Interaction:**
- Answer-to-Graph Bridge: synchronized split view with Q&A (left) and graph (right) panels
- Graph-First Landing: show hub entities immediately when opening processed investigation
- Conversational Investigation: Q&A maintains session context across questions
- Desktop-only: 1280px min width, 720px min height, with subtle warning below minimum
- Default 40/60 split, resizable divider (min 25% per panel), Q&A prose max-width 65ch
- Investigation list: CSS Grid auto-fill with minmax(320px, 1fr)
- Processing view → Split view crossfade transition on first entity extraction

**From UX — Accessibility (MVP):**
- Semantic HTML landmarks: header, nav, main, aside
- `aria-live="polite"` for streaming answers, processing status, toasts
- Entity Detail Card as non-focus-trapping dialog (user may interact with Q&A while card is open)
- All shadcn/ui keyboard accessibility maintained
- Focus management: modals trap focus, closing returns focus to trigger
- Graph keyboard navigation deferred to v2

### FR Coverage Map

- FR1: Epic 2 — Create investigation
- FR2: Epic 2 — List investigations
- FR3: Epic 2 — Delete investigation (cascading)
- FR4: Epic 2 — Open investigation workspace
- FR5: Epic 2 — Bulk PDF upload
- FR6: Epic 2 — Drag-and-drop folder upload
- FR7: Epic 2 — PDF text extraction
- FR8: Epic 2 — Immutable document storage
- FR9: Epic 2 — Document list with processing status
- FR10: Epic 2 — View extracted text
- FR11: Epic 3 — Entity extraction via local LLM
- FR12: Epic 3 — Relationship detection
- FR13: Epic 3 — Knowledge graph storage
- FR14: Epic 3 — Confidence scoring
- FR15: Epic 3 — Provenance chain maintenance
- FR16: Epic 3 — Vector embedding generation
- FR17: Epic 5 — Natural language question input
- FR18: Epic 5 — Query translation (NL → Cypher/vector)
- FR19: Epic 5 — GRAPH FIRST grounded answers
- FR20: Epic 5 — Source citations in answers
- FR21: Epic 5 — Citation click-through to source passage
- FR22: Epic 5 — "No connection found" response
- FR23: Epic 4 — Interactive graph view
- FR24: Epic 4 — Dynamic on-demand node loading
- FR25: Epic 4 — Entity detail card on node click
- FR26: Epic 4 — Relationship details on edge click
- FR27: Epic 4 — Neighborhood expansion
- FR28: Epic 4 — Filter by entity type
- FR29: Epic 4 — Filter by source document
- FR30: Epic 4 — Entity search with graph highlighting
- FR31: Epic 2 — Async document processing via job queue
- FR32: Epic 2 — Real-time progress updates (SSE)
- FR33: Epic 2 — Per-document processing status display
- FR34: Epic 3 — Live entity discovery during processing
- FR35: Epic 6 — Failed document marking with retry
- FR36: Epic 6 — Auto-retry on LLM recovery
- FR37: Epic 6 — Manual retry trigger
- FR38: Epic 6 — Data preservation on partial failure
- FR39: Epic 6 — Degraded mode (graph works without LLM)
- FR40: Epic 6 — Service status display
- FR41: Epic 1 — Docker Compose single-command deployment
- FR42: Epic 1 — Health check endpoints
- FR43: Epic 1 — LLM model readiness detection
- FR44: Epic 1 — Hardware insufficiency error messages
- FR45: Epic 3 — Document-level confidence indicators
- FR46: Epic 3 — Entity-level confidence scores
- FR47: Epic 4 — Relationship evidence inspection

## Epic List

### Epic 1: Project Foundation & Infrastructure Setup
Investigator (admin) can deploy the complete OSINT system with a single `docker compose up` command, verify all 7 services are healthy via a status page, and confirm LLM models are loaded and ready before proceeding.

**FRs covered:** FR41, FR42, FR43, FR44

### Epic 2: Investigation & Document Management
Investigator can create an investigation, bulk-upload PDFs (drag-and-drop), see real-time processing progress via SSE, view the document list with per-document status, and read the extracted text of any processed document. Documents are stored immutably with checksum verification.

**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR8, FR9, FR10, FR31, FR32, FR33

### Epic 3: Entity Extraction & Knowledge Graph Construction
After document upload, the system automatically extracts people, organizations, and locations with relationships and confidence scores using the local LLM. Entities appear in real-time as documents process. Every extracted fact maintains a complete provenance chain back to the source passage. Vector embeddings are generated for semantic search.

**FRs covered:** FR11, FR12, FR13, FR14, FR15, FR16, FR34, FR45, FR46

### Epic 4: Graph Visualization & Exploration
Investigator opens an investigation and sees an interactive knowledge graph showing hub entities. They can click nodes for entity detail cards, click edges for relationship evidence, expand neighborhoods, filter by entity type or source document, and search for entities with graph highlighting.

**FRs covered:** FR23, FR24, FR25, FR26, FR27, FR28, FR29, FR30, FR47

### Epic 5: Natural Language Q&A with Source Citations
Investigator asks natural language questions like "How is Person X connected to Company Y?" and receives grounded answers with clickable source citations. The GRAPH FIRST pipeline ensures zero hallucinated facts — every claim traces to a specific document passage. Answers stream progressively via SSE. Conversation context is maintained across questions.

**FRs covered:** FR17, FR18, FR19, FR20, FR21, FR22

### Epic 6: System Resilience & Error Recovery
The system handles failures gracefully across all services. Failed documents are marked with retry option (auto and manual). Individual service failures degrade functionality without crashing the app. Graph browsing works when LLM is down. Successfully processed data is never lost from partial failures. Clear service status is always visible.

**FRs covered:** FR35, FR36, FR37, FR38, FR39, FR40

---

## Epic 1: Project Foundation & Infrastructure Setup

Admin can deploy the complete OSINT system with a single `docker compose up` command, verify all 7 services are healthy via a status page, and confirm LLM models are loaded and ready before proceeding.

### Story 1.1: Monorepo Scaffolding & Docker Compose Infrastructure

As an administrator,
I want to run a single `docker compose up` command and have all infrastructure services start successfully,
So that I have a working foundation to build the application on.

**Acceptance Criteria:**

**Given** a fresh clone of the repository
**When** the administrator runs `docker compose up` from the docker/ directory
**Then** all 7 services start: app (placeholder), web (placeholder), postgres, neo4j, qdrant, redis, ollama
**And** named volumes are created for postgres-data, neo4j-data, qdrant-data, redis-data, ollama-models
**And** the storage/ directory is bind-mounted for document storage
**And** all services communicate on a single Docker bridge network

**Given** the dev compose file exists
**When** the administrator runs `docker compose -f docker-compose.dev.yml up`
**Then** only infrastructure services start: postgres, neo4j, qdrant, redis, ollama
**And** ports are exposed for native app development (PostgreSQL 5432, Neo4j 7474/7687, Qdrant 6333, Redis 6379, Ollama 11434)

**Given** the monorepo is initialized
**When** a developer inspects the project structure
**Then** `apps/web/` contains a React + Vite SPA scaffold (created via create-vite react-swc-ts template, shadcn/ui initialized)
**And** `apps/api/` contains a FastAPI + Celery scaffold (created via uv init, dependencies added)
**And** `docker/` contains both compose files, Dockerfiles, and nginx.conf
**And** `scripts/` contains generate-api-types.sh and dev.sh
**And** `storage/.gitkeep` exists
**And** `.env.example` documents all required environment variables

### Story 1.2: Backend Health Checks & Model Readiness

As an administrator,
I want to see the health status of every service and know when LLM models are loaded,
So that I can verify the system is ready before starting an investigation.

**Acceptance Criteria:**

**Given** all services are running
**When** a client sends `GET /api/v1/health/`
**Then** the response includes status for each service: postgres, neo4j, qdrant, redis, ollama
**And** each service reports "healthy", "unhealthy", or "unavailable" with a detail message
**And** Ollama status includes model readiness for qwen3.5:9b and qwen3-embedding:8b
**And** the response follows RFC 7807 format on errors

**Given** Ollama is running but models are not yet downloaded
**When** a client sends `GET /api/v1/health/`
**Then** the Ollama status reports "unhealthy" with detail: "Models not ready: qwen3.5:9b, qwen3-embedding:8b"
**And** a `models_ready` boolean field is `false`

**Given** the system is running on hardware below minimum spec
**When** the health endpoint detects insufficient resources
**Then** the response includes a warning with clear message about minimum requirements (16GB RAM, 8GB VRAM)

**Given** the FastAPI app starts
**When** the application initializes
**Then** database connections are established to PostgreSQL (SQLModel), Neo4j (driver), Qdrant (client), Redis (client)
**And** Alembic migrations run automatically on startup
**And** Loguru is configured for structured logging to stdout
**And** CORS is configured for localhost origins only (5173, 80)

### Story 1.3: Frontend Shell with System Status Page

As an administrator,
I want to open the application in my browser and see the system status with all service health indicators,
So that I can confirm everything is operational before I start working.

**Acceptance Criteria:**

**Given** the frontend application is running
**When** the administrator navigates to `/status`
**Then** a System Status page displays health status for all services (postgres, neo4j, qdrant, redis, ollama)
**And** each service shows a clear healthy/unhealthy/unavailable indicator
**And** Ollama section shows model readiness for each required model
**And** the page auto-refreshes health data on a reasonable interval

**Given** the frontend is built and deployed via Nginx
**When** the administrator navigates to `localhost` (port 80)
**Then** the application loads in the dark theme (default)
**And** TanStack Router handles routes: `/` (placeholder), `/investigations/:id` (placeholder), `/status`
**And** the root layout includes a persistent status bar showing overall system health

**Given** the OpenAPI type generation pipeline is configured
**When** a developer runs `scripts/generate-api-types.sh`
**Then** TypeScript types are generated from the FastAPI OpenAPI spec into `src/lib/api-types.generated.ts`
**And** the openapi-fetch client in `src/lib/api-client.ts` uses these generated types
**And** the health endpoint call in the Status page is fully typed

**Given** the viewport is below 1280px width
**When** the application renders
**Then** a subtle warning message appears: "OSINT is designed for screens 1280px and wider"

---

## Epic 2: Investigation & Document Management

Investigator can create an investigation, bulk-upload PDFs (drag-and-drop), see real-time processing progress via SSE, view the document list with per-document status, and read the extracted text of any processed document. Documents are stored immutably with checksum verification.

### Story 2.1: Investigation CRUD API & List View

As an investigator,
I want to create, view, and delete investigations,
So that I can organize my document collections into separate workspaces.

**Acceptance Criteria:**

**Given** the investigator is on the home page
**When** they click "New Investigation" and enter a name and description
**Then** a new investigation is created with a UUID and timestamps
**And** they are redirected to the investigation workspace

**Given** investigations exist
**When** the investigator navigates to `/`
**Then** the investigation list displays as cards in a CSS Grid layout (auto-fill, minmax(320px, 1fr))
**And** each card shows investigation name, description, creation date, and document count
**And** data is fetched via TanStack Query from `GET /api/v1/investigations/`

**Given** an investigation exists
**When** the investigator clicks delete and confirms
**Then** the investigation and all associated data are deleted (cascading: Neo4j → Qdrant → filesystem → PostgreSQL)
**And** the investigation disappears from the list

**Given** the investigator clicks on an investigation card
**When** the workspace loads at `/investigations/:id`
**Then** the investigation header shows name and description
**And** the workspace displays the document management area (upload zone + document list)

**Given** the backend receives a `POST /api/v1/investigations/`
**When** the request body contains name and optional description
**Then** the investigation is persisted in PostgreSQL via SQLModel
**And** the Alembic migration has created the `investigations` table
**And** a storage directory `storage/{investigation_id}/` is created on disk

### Story 2.2: PDF Upload with Immutable Storage

As an investigator,
I want to upload multiple PDF files at once by dragging a folder into the upload area,
So that I can quickly ingest all my investigation documents.

**Acceptance Criteria:**

**Given** the investigator is in an investigation workspace
**When** they drag and drop PDF files or a folder onto the upload area
**Then** each file is validated (PDF MIME type, file size limit)
**And** files are uploaded to `POST /api/v1/investigations/{id}/documents/`
**And** immediate feedback shows each file as "uploading"

**Given** a valid PDF is uploaded
**When** the backend receives the file
**Then** the file is stored at `storage/{investigation_id}/{document_id}.pdf`
**And** the stored file is byte-for-byte identical to the uploaded file (SHA-256 checksum computed and stored)
**And** a document record is created in PostgreSQL with metadata: filename, size, checksum, status="queued"
**And** the document is never modified, re-encoded, or compressed

**Given** multiple files are uploaded simultaneously
**When** the backend processes the uploads
**Then** each file gets its own document record and UUID
**And** bulk upload of 50+ documents completes without failure

**Given** an invalid file is uploaded (non-PDF, corrupted)
**When** the file middleware validates the upload
**Then** the upload is rejected with an RFC 7807 error response
**And** a clear error message indicates why the file was rejected

### Story 2.3: Async Document Processing Pipeline with Text Extraction

As an investigator,
I want my uploaded documents to be processed automatically in the background with text extracted,
So that I don't have to wait and can continue working while documents are processed.

**Acceptance Criteria:**

**Given** a document has been uploaded with status "queued"
**When** the Celery worker picks up the processing job
**Then** the document status transitions through: queued → extracting_text → complete
**And** text content is extracted from the PDF using PyMuPDF
**And** extracted text is stored separately from the original document (derived data separation)
**And** text extraction completes in <30 seconds per 100 pages

**Given** documents are queued for processing
**When** the Celery worker processes them
**Then** jobs are processed sequentially from the Redis-backed queue
**And** the queue persists across worker restarts (Redis AOF)
**And** each processing stage publishes SSE events via Redis pub/sub

**Given** text extraction fails for a document
**When** PyMuPDF encounters an error
**Then** the document status is set to "failed"
**And** the error is logged via Loguru with document_id and error detail
**And** a `document.failed` SSE event is published

### Story 2.4: Real-Time Processing Dashboard with SSE

As an investigator,
I want to see live progress as my documents are processed,
So that I know what's happening without manually refreshing.

**Acceptance Criteria:**

**Given** the investigator is in an investigation workspace with documents processing
**When** documents move through processing stages
**Then** SSE events are received via `GET /api/v1/events/{investigation_id}`
**And** events follow the defined format: `document.queued`, `document.processing`, `document.complete`, `document.failed`
**And** events arrive within 1 second of the state change

**Given** the frontend receives SSE events
**When** a document's status changes
**Then** the processing dashboard updates the per-document status card in real-time (no page refresh)
**And** status cards show: queued, extracting text, complete, or failed
**And** the SSE connection uses `@microsoft/fetch-event-source` piped into TanStack Query cache

**Given** the SSE connection drops
**When** the client detects disconnection
**Then** fetch-event-source auto-reconnects
**And** on reconnection, the frontend fetches current state from the REST API to reconcile

**Given** the investigator navigates to the document list
**When** they view `GET /api/v1/investigations/{id}/documents/`
**Then** each document shows: filename, file size, processing status, and upload timestamp
**And** completed documents show a link to view extracted text

### Story 2.5: Extracted Text Viewer

As an investigator,
I want to read the text extracted from my documents,
So that I can verify the system processed them correctly.

**Acceptance Criteria:**

**Given** a document has been successfully processed (status: complete)
**When** the investigator clicks "View Text" on a document
**Then** the extracted text is displayed via `GET /api/v1/investigations/{id}/documents/{doc_id}/text`
**And** the text is presented in a readable format preserving basic structure (paragraphs, headings)

**Given** a document has status "queued" or "processing"
**When** the investigator views the document list
**Then** the "View Text" action is disabled with a clear indicator that processing is in progress

**Given** a document has status "failed"
**When** the investigator views the document list
**Then** the document shows the failure reason
**And** no extracted text is available

---

## Epic 3: Entity Extraction & Knowledge Graph Construction

After document upload, the system automatically extracts people, organizations, and locations with relationships and confidence scores using the local LLM. Entities appear in real-time as documents process. Every extracted fact maintains a complete provenance chain back to the source passage. Vector embeddings are generated for semantic search.

### Story 3.1: Document Chunking & LLM Integration Layer

As a developer,
I want the document processing pipeline to chunk extracted text and communicate with Ollama,
So that entities can be extracted from manageable text segments with the local LLM.

**Acceptance Criteria:**

**Given** a document has completed text extraction (from Epic 2)
**When** the processing pipeline continues
**Then** the extracted text is split into chunks with page/passage tracking preserved
**And** each chunk records its source document ID, page number(s), and character offsets
**And** chunks are stored in PostgreSQL with their provenance metadata

**Given** the Ollama integration module exists at `app/llm/client.py`
**When** a service calls the LLM client
**Then** requests are sent to the local Ollama instance (qwen3.5:9b)
**And** zero outbound network calls are made — all inference is local
**And** prompts are defined in `app/llm/prompts.py` (never hardcoded in services)

**Given** Ollama is unavailable during chunk processing
**When** the LLM client fails to connect
**Then** the error is caught and logged via Loguru
**And** the document status transitions to "failed" with a clear error message
**And** a `document.failed` SSE event is published

### Story 3.2: Entity & Relationship Extraction via Local LLM

As an investigator,
I want the system to automatically find people, organizations, and locations in my documents and detect how they're connected,
So that I don't have to manually read every document to map relationships.

**Acceptance Criteria:**

**Given** document chunks exist from Story 3.1
**When** the Celery worker runs entity extraction on each chunk
**Then** people, organizations, and locations are extracted using Ollama qwen3.5:9b
**And** relationships are detected between entities (WORKS_FOR, KNOWS, LOCATED_AT, MENTIONED_IN)
**And** each entity and relationship is assigned a confidence score (0.0–1.0)
**And** the document status transitions through: extracting_entities stage
**And** `entity.discovered` SSE events are published as entities are found

**Given** entities are extracted from a chunk
**When** they are stored in Neo4j
**Then** nodes are created with labels: Person, Organization, Location (PascalCase)
**And** relationships use types: WORKS_FOR, KNOWS, LOCATED_AT, MENTIONED_IN (UPPER_SNAKE_CASE)
**And** all node and relationship properties use snake_case
**And** each entity stores: name, type, confidence_score, investigation_id
**And** each relationship stores: type, confidence_score, source_chunk_id
**And** database transactions are atomic — no partially-written entities

**Given** the same entity appears across multiple chunks or documents
**When** the extraction pipeline encounters a duplicate
**Then** the existing entity is reused (matched by name + type + investigation)
**And** additional source references are added to the entity
**And** confidence scores are updated based on multiple corroborating sources

**Given** extraction produces results
**When** the investigator views the processing dashboard
**Then** entities appear in real-time via SSE as each document processes (FR34)
**And** entity count updates live on the investigation workspace

### Story 3.3: Provenance Chain & Evidence Storage

As an investigator,
I want every extracted fact to trace back to the exact document passage it came from,
So that I can verify any connection the system finds.

**Acceptance Criteria:**

**Given** an entity or relationship is extracted
**When** it is stored in Neo4j
**Then** a complete provenance chain is maintained: entity/relationship → source chunk → document → page/passage
**And** the source chunk text is preserved and linkable
**And** provenance data is stored as Neo4j properties and relationships (MENTIONED_IN edges to Document nodes)

**Given** the API serves entity data
**When** a client requests `GET /api/v1/investigations/{id}/entities/{entity_id}`
**Then** the response includes the entity's properties, relationships, and source documents
**And** each source reference includes: document filename, page number, passage text
**And** zero orphaned citations exist (every citation resolves to an actual document chunk)

**Given** a relationship between two entities exists
**When** the evidence is queried
**Then** all supporting document passages are returned
**And** evidence strength is indicated (single source vs. corroborated across multiple documents)

### Story 3.4: Vector Embedding Generation & Storage

As an investigator,
I want my document content to be semantically searchable,
So that natural language queries can find relevant passages even when exact keywords don't match.

**Acceptance Criteria:**

**Given** document chunks exist
**When** the processing pipeline reaches the embedding stage
**Then** vector embeddings are generated for each chunk using Ollama qwen3-embedding:8b
**And** embeddings are stored in the single Qdrant collection with `investigation_id` as a payload filter
**And** each embedding links to its source chunk ID for provenance
**And** the document status transitions through: embedding stage → complete

**Given** the full pipeline runs on a 100-page PDF
**When** processing completes (text extraction + entity extraction + embedding)
**Then** total processing time is <15 minutes on minimum hardware (16GB RAM, 8GB VRAM)

**Given** embedding generation fails for a chunk
**When** Ollama returns an error
**Then** the failure is logged with chunk details
**And** already-stored entities and relationships from previous stages remain intact (no data loss)

### Story 3.5: Document-Level & Entity-Level Confidence Display

As an investigator,
I want to see confidence indicators showing how well each document was processed and how reliable each entity is,
So that I know which results to trust and which documents to manually review.

**Acceptance Criteria:**

**Given** documents have been processed with entity extraction
**When** the investigator views the document list
**Then** each document shows an extraction quality indicator (e.g., high/medium/low confidence based on average entity confidence)
**And** low-confidence documents are visually distinct (FR45)

**Given** entities have been extracted with confidence scores
**When** the investigator views entity information via the API
**Then** each entity includes its confidence score (0.0–1.0)
**And** the API response from `GET /api/v1/investigations/{id}/entities/` includes confidence_score per entity (FR46)

**Given** the processing dashboard is showing live updates
**When** a document completes processing
**Then** the confidence indicator appears on the document status card
**And** the overall investigation summary updates entity counts by type (people, organizations, locations)

---

## Epic 4: Graph Visualization & Exploration

Investigator opens an investigation and sees an interactive knowledge graph showing hub entities. They can click nodes for entity detail cards, click edges for relationship evidence, expand neighborhoods, filter by entity type or source document, and search for entities with graph highlighting.

### Story 4.1: Graph API & Subgraph Queries

As an investigator,
I want the backend to serve graph data efficiently for visualization,
So that the frontend can load and display subgraphs on demand without fetching the entire graph.

**Acceptance Criteria:**

**Given** an investigation has entities and relationships in Neo4j
**When** a client sends `GET /api/v1/investigations/{id}/graph/` with viewport/pagination parameters
**Then** the response returns a subgraph: nodes (entities) and edges (relationships) limited to the requested scope
**And** nodes include: id, name, type, confidence_score, relationship_count (for hub detection)
**And** edges include: id, source, target, type, confidence_score
**And** the response is structured for direct consumption by Cytoscape.js

**Given** a client requests neighborhood expansion
**When** `GET /api/v1/investigations/{id}/graph/neighbors/{entity_id}` is called
**Then** the response returns the entity's immediate neighbors and connecting edges
**And** the response completes in <1 second

**Given** no entities exist yet (empty investigation or still processing)
**When** the graph endpoint is called
**Then** an empty graph response is returned (empty nodes/edges arrays)
**And** no error is thrown

### Story 4.2: Interactive Graph Canvas with Cytoscape.js

As an investigator,
I want to see an interactive graph of entities and relationships when I open my investigation,
So that I can visually explore the connections the system found in my documents.

**Acceptance Criteria:**

**Given** an investigation has processed entities
**When** the investigator opens the investigation workspace
**Then** the graph canvas renders using Cytoscape.js via a custom `useCytoscape` hook
**And** the Graph-First Landing shows top hub entities (most connected nodes) with a clean layout
**And** entity types are color-coded: Person (amber), Organization (blue), Location (green)
**And** node border thickness reflects confidence score
**And** the graph renders up to 500 visible nodes in <2 seconds

**Given** the workspace uses the Answer-to-Graph Bridge layout
**When** the investigator views the investigation
**Then** the workspace splits into Q&A panel (left, 40%) and graph panel (right, 60%)
**And** the split divider is resizable with minimum 25% per panel
**And** the graph canvas fills 100% of its panel at any size

**Given** the graph contains more entities than can fit in the viewport
**When** the graph loads initially
**Then** only hub nodes and their immediate connections are loaded (viewport-based loading)
**And** no artificial upper limit is imposed on graph size
**And** additional nodes are fetched on demand as the user explores

**Given** `prefers-reduced-motion` is enabled
**When** graph layout changes occur
**Then** all animations are reduced to instant state changes

### Story 4.3: Node & Edge Interaction with Entity Detail Card

As an investigator,
I want to click on entities and relationships in the graph to see their details and evidence,
So that I can inspect the facts behind any connection.

**Acceptance Criteria:**

**Given** the graph is displayed with entities
**When** the investigator clicks a node
**Then** an Entity Detail Card appears showing: name, type, confidence score, relationships list, and source documents
**And** the card is a non-focus-trapping dialog (investigator can interact with Q&A panel while card is open)
**And** the card's floating position adapts to available graph canvas space

**Given** the graph shows relationships between entities
**When** the investigator clicks an edge
**Then** relationship details appear: type, confidence score, and source citation(s)
**And** each source citation includes document filename, page number, and passage text (FR47)
**And** the investigator can inspect all evidence supporting the relationship

**Given** an entity node is displayed
**When** the investigator double-clicks it (or clicks expand)
**Then** the node's neighborhood is loaded via the neighbors API
**And** new neighbor nodes animate in (400ms ease-out) and the layout stabilizes
**And** expansion completes in <1 second

### Story 4.4: Graph Filtering by Entity Type & Source Document

As an investigator,
I want to filter the graph to show only specific entity types or entities from specific documents,
So that I can focus on the connections most relevant to my current line of inquiry.

**Acceptance Criteria:**

**Given** the graph displays entities of multiple types
**When** the investigator toggles entity type filters (people, organizations, locations)
**Then** non-matching nodes and their edges are hidden with a smooth opacity + scale animation (200ms)
**And** the graph layout adjusts to the remaining visible nodes
**And** filter state persists within the session

**Given** the investigation has multiple source documents
**When** the investigator selects a document filter
**Then** only entities and relationships sourced from the selected document(s) are shown
**And** entities from other documents are hidden

**Given** multiple filters are active (type + document)
**When** the investigator views the graph
**Then** both filters apply simultaneously (AND logic)
**And** clearing all filters restores the full graph view

### Story 4.5: Entity Search with Graph Highlighting

As an investigator,
I want to search for specific entities by name and see them highlighted in the graph,
So that I can quickly locate known persons, organizations, or locations.

**Acceptance Criteria:**

**Given** the graph is displayed
**When** the investigator types a search query in the entity search input
**Then** matching entities are returned from `GET /api/v1/investigations/{id}/entities/` with search parameter
**And** results appear in <500 milliseconds
**And** matching nodes in the graph are highlighted with a glow effect (opacity transition + subtle pulse, 600ms)

**Given** a search result is selected
**When** the investigator clicks on a search result
**Then** the graph centers on and highlights the matching node
**And** the node's neighborhood is expanded if not already loaded

**Given** the investigator clears the search
**When** the search input is emptied
**Then** all highlighting is removed and the graph returns to its default visual state

---

## Epic 5: Natural Language Q&A with Source Citations

Investigator asks natural language questions like "How is Person X connected to Company Y?" and receives grounded answers with clickable source citations. The GRAPH FIRST pipeline ensures zero hallucinated facts — every claim traces to a specific document passage. Answers stream progressively via SSE. Conversation context is maintained across questions.

### Story 5.1: GRAPH FIRST Query Pipeline

As an investigator,
I want to ask natural language questions and have them translated into graph and vector searches,
So that answers come from my actual documents rather than AI speculation.

**Acceptance Criteria:**

**Given** an investigation has entities, relationships, and embeddings
**When** the investigator submits a question via `POST /api/v1/investigations/{id}/query/`
**Then** the LLM translates the natural language question into Cypher graph queries and vector search operations
**And** the Cypher query executes against Neo4j to find entity paths and relationships
**And** the vector search executes against Qdrant (filtered by investigation_id) to find semantically relevant chunks
**And** results from both sources are merged with their provenance chains

**Given** the query pipeline processes results
**When** grounded results with provenance are available
**Then** the LLM formats the results as cited prose — it formats and presents, never synthesizes or infers
**And** every fact in the answer maps to a specific source document passage
**And** the LLM never presents speculation, inference, or "likely" connections as facts (NFR22)

**Given** the graph cannot answer a question
**When** no relevant entities, relationships, or chunks are found
**Then** the system returns "No connection found in your documents" (FR22)
**And** the response is not a fabricated or hedged answer

**Given** a question is submitted
**When** the pipeline executes
**Then** SSE events are published: `query.translating` → `query.searching` → `query.streaming` → `query.complete`
**And** streaming begins within 5 seconds

### Story 5.2: Answer Streaming & Q&A Panel

As an investigator,
I want to see answers stream in progressively with citations I can click,
So that I get results quickly and can immediately verify any fact.

**Acceptance Criteria:**

**Given** a query is processing
**When** the answer begins streaming
**Then** the Q&A panel (left side of split view) displays answer text progressively via SSE `query.streaming` events
**And** answer text uses Perplexity-style cited prose: entity names are highlighted and clickable, citations appear as superscript numbers
**And** query status updates show in the panel: translating → searching → streaming answer

**Given** answer streaming completes
**When** the `query.complete` SSE event arrives
**Then** the complete answer is displayed with all citations and entity highlights
**And** suggested follow-up questions appear below the answer
**And** the total time from question to answer is <30 seconds on minimum hardware

**Given** the query fails
**When** a `query.failed` SSE event arrives
**Then** a clear error message is displayed in the Q&A panel
**And** the investigator can retry or ask a different question

**Given** the investigator has asked previous questions
**When** they ask a follow-up question
**Then** the conversation history is maintained within the session
**And** the LLM uses prior conversation context for query translation (conversational investigation)

### Story 5.3: Citation Click-Through Viewer

As an investigator,
I want to click any citation in an answer and see the original document passage,
So that I can verify every fact the system presents.

**Acceptance Criteria:**

**Given** an answer contains superscript citation numbers
**When** the investigator clicks a citation number
**Then** a Citation Modal opens showing the original source passage with the relevant text highlighted
**And** the modal displays: document filename, page number, and surrounding context
**And** the modal is built on Radix UI Dialog (inherits focus trap, aria-modal, Escape handling)
**And** modal enters with fade in + scale from 0.95 (150ms ease-out)

**Given** an answer contains highlighted entity names
**When** the investigator clicks an entity name in the answer text
**Then** the graph panel centers on and highlights that entity node
**And** the entity's neighborhood is expanded if not already loaded
**And** this implements the Answer-to-Graph Bridge synchronization

**Given** a citation references a specific passage
**When** the citation is resolved
**Then** the passage text matches exactly what was extracted from the document
**And** every citation resolves to an actual document chunk (zero orphaned citations)
**And** 100% of facts in the answer are traceable to a specific source document passage (NFR21)

---

## Epic 6: System Resilience & Error Recovery

The system handles failures gracefully across all services. Failed documents are marked with retry option (auto and manual). Individual service failures degrade functionality without crashing the app. Graph browsing works when LLM is down. Successfully processed data is never lost from partial failures. Clear service status is always visible.

### Story 6.1: Failed Document Detection & Manual Retry

As an investigator,
I want failed documents to be clearly marked and retryable,
So that a single failure doesn't block my entire investigation.

**Acceptance Criteria:**

**Given** document processing fails at any stage (text extraction, entity extraction, embedding)
**When** the Celery worker catches the error
**Then** the document status is set to "failed" with the failure stage and error detail recorded
**And** a `document.failed` SSE event is published with `{document_id, stage, error}`
**And** all successfully processed data from prior stages remains intact (no rollback of completed work)

**Given** a document is in "failed" status
**When** the investigator views the document list
**Then** the document shows "failed — retry available" with the failure reason
**And** a retry button is visible on the failed document

**Given** the investigator clicks retry on a failed document
**When** `POST /api/v1/investigations/{id}/documents/{doc_id}/retry` is called
**Then** the document is re-queued for processing from the failed stage
**And** the document status updates to "queued" and SSE events resume
**And** previously completed stages are not re-executed (resume from failure point)

### Story 6.2: Auto-Retry on Service Recovery

As an investigator,
I want failed documents to automatically retry when the LLM comes back online,
So that I don't have to manually babysit the processing queue.

**Acceptance Criteria:**

**Given** documents failed because Ollama was unavailable
**When** the health check detects Ollama has recovered
**Then** failed documents are automatically re-queued for processing
**And** SSE events notify the frontend that retries are in progress
**And** the investigator sees status transition from "failed" back to processing stages

**Given** the Celery worker restarts
**When** the worker comes back online
**Then** pending jobs in the Redis queue are preserved (Redis AOF persistence)
**And** processing resumes from where it left off
**And** no jobs are lost or duplicated

**Given** Ollama repeatedly fails
**When** auto-retry triggers multiple times
**Then** retries use exponential backoff to avoid overwhelming a struggling service
**And** after a maximum retry count, the document remains in "failed" status for manual intervention

### Story 6.3: Per-Service Graceful Degradation

As an investigator,
I want the application to keep working partially when individual services are down,
So that I can still use available features instead of facing a completely broken app.

**Acceptance Criteria:**

**Given** Ollama is down
**When** the investigator uses the application
**Then** graph browsing and visualization work normally (Neo4j is independent)
**And** natural language queries return: "LLM service unavailable — try again shortly"
**And** document upload still queues for later processing
**And** the status bar shows Ollama as unavailable

**Given** Neo4j is down
**When** the investigator uses the application
**Then** document upload and queuing still work
**And** graph pages show a clear error: "Graph database unavailable"
**And** Q&A queries that depend on graph return a clear error

**Given** Qdrant is down
**When** the investigator uses the application
**Then** graph queries work (Neo4j is independent)
**And** natural language queries fall back to graph-only results (no vector search)
**And** the status bar indicates reduced search capability

**Given** any service recovers
**When** the health check detects the recovery
**Then** the application restores full functionality automatically without requiring a restart (NFR27)
**And** a `service.status` SSE event notifies the frontend of the status change

### Story 6.4: Service Status Display & Error Boundaries

As an investigator,
I want to always know which services are working and have the UI handle errors without crashing,
So that I can make informed decisions about when to trust results and when to wait.

**Acceptance Criteria:**

**Given** the application is running
**When** the investigator views any page
**Then** a persistent status bar in the root layout shows overall system health
**And** the status bar indicates: all healthy, degraded (some services down), or critical (core services down)
**And** clicking the status bar navigates to the full `/status` page with per-service detail

**Given** the Q&A panel encounters a JavaScript error
**When** a React error boundary catches the error
**Then** only the Q&A panel shows an error fallback — the graph panel continues working
**And** the error boundary provides a "reload panel" action

**Given** the graph canvas encounters a rendering error
**When** the `useCytoscape` hook catches the error
**Then** an empty graph with an error message is shown — the Q&A panel continues working
**And** the workspace does not crash entirely

**Given** the SSE connection fails repeatedly
**When** fetch-event-source fails to reconnect after 3 attempts
**Then** a degraded status indicator appears in the UI
**And** the frontend falls back to REST API polling for current state
**And** a toast notification informs the investigator that live updates are temporarily unavailable
