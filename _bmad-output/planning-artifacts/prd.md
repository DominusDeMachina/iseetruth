---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
  - step-12-complete
workflow_completed: true
lastEdited: '2026-03-06'
editHistory:
  - date: '2026-03-06'
    changes: 'Added Quick Reference overview section; Made NFR13 measurable (<500ms threshold)'
inputDocuments:
  - '_bmad-output/planning-artifacts/product-brief-OSINT-2026-03-05.md'
  - '_bmad-output/brainstorming/brainstorming-session-2026-03-05-1200.md'
documentCounts:
  briefs: 1
  research: 0
  brainstorming: 1
  projectDocs: 0
classification:
  projectType: 'Web App (local-first, self-hosted)'
  domain: 'OSINT / Investigation Tooling'
  complexity: 'high'
  projectContext: 'greenfield'
workflowType: 'prd'
---

# Product Requirements Document - OSINT

**Author:** Gennadiy
**Date:** 2026-03-05

### Quick Reference

| Attribute | Value |
|-----------|-------|
| **What** | Local-first investigation platform — ingest documents, extract entities, query connections with source citations |
| **Who** | Investigative journalists and OSINT researchers protecting confidential sources |
| **MVP** | Upload PDFs → auto-extract entities → graph visualization → natural language Q&A with citations. All local. |
| **Tech** | Next.js + FastAPI/Celery + Ollama (Qwen 2.5 7B) + Neo4j + Qdrant + PostgreSQL, Docker Compose |
| **Privacy** | Zero outbound network calls. All processing on-device. No cloud APIs. |
| **Key Metric** | 80% of users reach "aha" moment (cited answer from their documents) within 30 minutes |
| **Hardware** | 16GB RAM, 8GB VRAM minimum. Consumer laptop. |
| **Validation Gate** | 5 real users complete real investigations |

## Executive Summary

OSINT is a local-first investigation platform that enables journalists and OSINT researchers to uncover hidden connections in corruption investigations. Users ingest documents and the system automatically extracts entities (people, organizations, locations) and their relationships using local LLMs. Investigators then ask natural language questions like "How is the mayor connected to this construction company?" and receive answers with complete source citations — every fact traceable to its original document passage. All processing happens on the investigator's machine. No data leaves the laptop. No cloud APIs. No third parties to subpoena.

The primary user is an independent investigative journalist with no technical support, working under time pressure, protecting confidential sources. Secondary users include local law enforcement investigators and intelligence analysts operating under strict data sovereignty requirements.

The core technical insight: local LLMs have crossed the capability threshold for meaningful entity extraction on consumer hardware, making privacy-preserving investigation tooling feasible for the first time without enterprise budgets or cloud dependencies.

### What Makes This Special

**Privacy as trust, not just a feature.** The differentiation moment isn't the answer — it's the confidence to *use* the answer. When an investigator gets a response with a clickable citation back to the original passage, and knows that entire interaction happened locally, they trust it enough to publish. That combination — actionable intelligence with absolute privacy — doesn't exist at a price an independent journalist can afford.

**Graphs find what humans can't.** Corruption networks are webs, not lines. The critical link is often three or four hops away, buried across documents that were never meant to be read together. Human cognition can't hold enough relationships in working memory to surface these connections. A knowledge graph can — and with source citations, every discovered connection is verifiable.

**Radically accessible.** Zero API costs, runs on consumer hardware (16GB RAM, 8GB VRAM), open source. The same class of analysis that costs enterprises six figures is available to a freelance journalist with a laptop.

## Project Classification

| Attribute | Value |
|-----------|-------|
| **Project Type** | Web App (local-first, self-hosted) |
| **Domain** | OSINT / Investigation Tooling |
| **Complexity** | High — multi-database orchestration (Neo4j + Qdrant + PostgreSQL), local LLM pipeline, evidence integrity requirements, source protection stakes |
| **Project Context** | Greenfield |
| **Tech Stack** | Next.js frontend, FastAPI/Celery Python worker, Ollama (Qwen 2.5 7B), Neo4j, Qdrant, PostgreSQL, Redis |

## Success Criteria

### User Success

**First-Session Validation (the "aha" metric):**
- User uploads documents, asks a natural language question, and gets a verifiable answer with source citation — all within their first session
- Target: 80% of new users reach this moment within 30 minutes of first launch

**Investigation Completion:**
- A user runs a full investigation cycle: upload → extract → query → verify against source
- Target: 5 real users complete real investigations within 3 months of launch (MVP validation gate)

**Return Usage:**
- Users come back for new investigations — the tool becomes their starting point
- Target: 3+ users running second investigations within 6 months

**Impact (North Star):**
- Published investigations citing OSINT-surfaced facts
- Target: 10 published stories within 12 months
- Measurement: Community self-reporting, "wall of impact" showcase

### Business Success

**Community Traction:**

| Metric | 3-Month Target | 12-Month Target |
|--------|---------------|-----------------|
| GitHub stars | 100 | 500 |
| Active community members (Discord) | 20 | 100+ |
| Contributors | 2 | 5+ |
| Real investigations completed | 5 | 25 |

**Funding:**
- 12-month target: 1 small grant from journalism-focused foundation (Knight, Mozilla, Ford Foundation, First Look Media)
- Sustainability: Operational costs near zero through local-first architecture

### Technical Success

**Entity Extraction Quality:**
- Qwen 2.5 7B extracts people, organizations, and locations from corruption-domain documents with >80% precision
- Measured by: manual review of extraction results against 10 known-answer test documents

**Query Performance:**
- Natural language question → answer with citations in <30 seconds on minimum hardware (16GB RAM, 8GB VRAM)
- Graph path queries (how is A connected to B?) return in <10 seconds

**Processing Throughput:**
- Pipeline handles 100-page PDF in <15 minutes on minimum hardware
- Bulk upload of 50 documents queued and processed without failure

**Evidence Integrity:**
- Every fact in an answer links to a specific source passage
- Zero orphaned citations (every citation resolves to an actual document chunk)
- Source document is never modified by the system

### Measurable Outcomes

| Outcome | Metric | Target | Measurement Method |
|---------|--------|--------|-------------------|
| First-session success | Users reaching "aha" moment | 80% within 30 min | Local telemetry (opt-in) |
| MVP validation | Real investigations completed | 5 users | Direct outreach |
| Extraction accuracy | Precision on test corpus | >80% | Manual evaluation |
| Query latency | Question-to-answer time | <30 sec | Performance benchmarks |
| Privacy guarantee | Data exfiltration events | Zero | Architecture audit |

## Product Scope

**MVP Done Definition:**
Upload a folder of PDFs → system extracts entities automatically → see graph → ask "How is Person X connected to Company Y?" → get answer with citations → click citation to see original passage. All local. No auth. No cloud.

**Phased Roadmap:** MVP (PDF pipeline + graph + Q&A) → v1.1 (image OCR, entity merge, web ingestion) → v2 (auth, collaboration, integrations, export) → v3+ (intelligence platform). See [Project Scoping & Phased Development](#project-scoping--phased-development) for detailed breakdown.

## User Journeys

### Journey 1: Maria Breaks the Story (Primary User — Success Path)

**Maria** is an investigative reporter at a regional newspaper in Eastern Europe. She's been tipped off by a whistleblower that the deputy mayor has been funneling public construction contracts to shell companies linked to his brother-in-law. The whistleblower gave her a USB drive with 47 PDF documents — meeting minutes, contract awards, company registrations, bank transfer confirmations — and then went silent.

Maria has two weeks before the municipal elections. She knows the story is in these documents, but she's spent three days reading them and her spreadsheet of names and companies is already unmanageable. She can't see the pattern.

**Day 1 with OSINT.** Maria's colleague at another newsroom told her about it. She downloads the release, runs the install script, and opens the browser interface. She creates a new investigation — "Deputy Mayor Construction Contracts" — and drags her folder of 47 PDFs into the upload area. A progress bar shows documents being processed one by one. She makes coffee.

When she comes back, the dashboard shows: 23 people extracted, 14 organizations, 8 locations, and 67 relationships detected. She clicks into the graph view and sees a web of nodes she's never visualized before. The deputy mayor is at the center, but there are three companies she's never heard of connecting him to entities she hasn't investigated yet.

**The moment.** Maria types: "How is Deputy Mayor Horvat connected to GreenBuild LLC?" The system returns: "Deputy Mayor Horvat is connected to GreenBuild LLC through two paths: (1) Horvat signed contract award #2024-089 awarded to GreenBuild LLC [source: contract-award-089.pdf, page 3], and (2) Horvat's brother-in-law Marko Petrovic is registered director of Cascade Holdings, which owns 60% of GreenBuild LLC [source: company-registration-2021.pdf, page 1; ownership-filing.pdf, page 4]."

She clicks each citation. The original passages highlight in context. Every fact is traceable. And none of this ever left her laptop.

Maria publishes three days before the election. The deputy mayor doesn't get re-elected.

**Capabilities revealed:** Document upload (bulk), processing pipeline with progress feedback, entity extraction, relationship detection, graph visualization, natural language Q&A, source citations with click-through, investigation management.

### Journey 2: Maria Hits a Wall (Primary User — Edge Case)

Same investigation, different day. Maria uploads a batch of scanned documents — photocopies of handwritten meeting notes the whistleblower grabbed from a filing cabinet. The system processes them, but the extraction results are thin: only 3 entities found across 12 pages. The OCR struggled with the handwriting and the entity extraction couldn't make sense of the garbled text.

Maria sees a "low confidence" indicator on these documents in her document list. She opens the processed text view and sees the OCR output is mostly garbage. She can read the handwriting herself — she grew up reading her grandmother's letters in the same script.

**What she does:** For MVP, Maria works around it. She manually reads the key documents, and notes the names and connections she finds. She knows the system didn't catch everything, but the 35 PDFs it *did* process well have already given her more than her spreadsheet ever could. The low-confidence indicator told her which documents to check manually — she didn't waste time verifying the ones the system handled well.

**What she wishes she could do (v1.1+):** Manually add entities and relationships she found by reading the bad documents. Correct entity names the system got wrong. Merge "Dep. Mayor Horvat" and "Deputy Mayor Horvat" into one node.

**Capabilities revealed:** Processing confidence indicators per document, processed text preview, low-confidence flagging, graceful degradation when extraction fails. Future: manual entity creation, entity merge, relationship correction.

### Journey 3: Carlos Builds a Case File (Secondary User — Law Enforcement)

**Detective Carlos** works organized crime at a mid-sized city police department. He's investigating a contractor suspected of bribing city officials for building permits. His department can't afford Palantir, and the FBI isn't interested in a local case.

Carlos has 80+ documents: permit applications, inspection reports, bank records obtained via subpoena, and corporate filings from the secretary of state's website. He sets up OSINT on a department workstation (air-gapped from the internet, IT approved the Docker install).

His journey is similar to Maria's — upload, extract, query, explore the graph. But Carlos has one additional need: when he finds a connection, he needs to document the chain of evidence for the prosecutor. He can't just say "the system told me." He needs to show: this fact came from this document, which was obtained via this subpoena, and here's the exact passage.

**What OSINT gives him in MVP:** Every answer includes source citations. Carlos can click through to the original document passage for each fact in a connection chain. He screenshots these citation trails and includes them in his case file. It's manual, but it works — the system provides the raw material for evidence documentation.

**What he needs in v2+:** Export a connection path as a structured evidence chain document. Annotate documents with chain-of-custody metadata (how obtained, when, by whom). Flag connections as "verified" vs. "system-detected." Generate a printable evidence summary for the prosecutor.

**Capabilities revealed:** Same core pipeline as Maria. Additionally reveals need for: clear citation provenance, connection path display, document metadata visibility. Future: evidence chain export, custody metadata, verification workflow.

### Journey 4: Setting Up OSINT (Admin/Self-Install Journey)

**Alex** is a data journalist at a nonprofit newsroom. She's more technical than Maria — comfortable with the terminal, has Docker installed, has used Jupyter notebooks. Her editor asked her to evaluate OSINT for the team.

Alex clones the repo and reads the README. She runs `docker compose up` and waits while 6 services start and 3 Ollama models download (~8GB total). On her M2 MacBook Pro with 16GB RAM, the initial setup takes about 20 minutes (mostly model downloads). She opens `localhost:3000` and sees the investigation dashboard.

She creates a test investigation with a few public documents she pulled from OCCRP, and runs through the upload-extract-query flow. It works. She checks system resource usage — Neo4j and Ollama are the heaviest consumers, but the system is responsive.

**Where she hits friction:** The Ollama model download is slow on her office WiFi. There's no indication of which models are ready vs. still downloading. She has to check the terminal logs to confirm everything is running. When she first queries, it takes 45 seconds because the model is cold-loading — subsequent queries are faster.

**What makes setup successful:** Clear README with hardware requirements upfront. Single `docker compose up` command. Health check endpoint that shows all services status. First-run experience that confirms models are loaded before allowing queries.

**Capabilities revealed:** Docker Compose deployment, service health monitoring, model readiness detection, first-run setup flow, system status dashboard. Hardware requirements documentation, clear error messages when resources are insufficient.

### Journey Requirements Summary

| Capability Area | Journey 1 (Maria Success) | Journey 2 (Maria Edge) | Journey 3 (Carlos) | Journey 4 (Admin Setup) |
|----------------|--------------------------|------------------------|--------------------|-----------------------|
| Document upload (bulk) | Core | Core | Core | Test |
| Processing pipeline + progress | Core | Core | Core | Verify |
| Entity extraction | Core | Fails gracefully | Core | Test |
| Confidence indicators | — | Critical | Useful | — |
| Graph visualization | Core | Partial | Core | Test |
| Natural language Q&A | Core | Limited | Core | Test |
| Source citations + click-through | Core | Core | Critical | Test |
| Investigation CRUD | Core | Core | Core | Test |
| Processed text preview | — | Critical | Useful | — |
| Docker Compose deployment | — | — | — | Core |
| Service health monitoring | — | — | — | Critical |
| Model readiness check | — | — | — | Critical |

**MVP-Critical Capabilities** (required across journeys):
- Bulk PDF upload with progress feedback
- Entity extraction with confidence scoring
- Knowledge graph storage and visualization
- Natural language Q&A with verifiable source citations
- Investigation management (create, list, delete)
- Docker Compose single-command deployment
- Service health/readiness checks

**Post-MVP Capabilities** (revealed by edge cases):
- Manual entity creation/correction/merge
- Evidence chain export
- Chain-of-custody metadata
- Advanced OCR for handwritten/degraded documents
- System resource monitoring dashboard

## Domain-Specific Requirements

### Data Sovereignty & Privacy Architecture

**MVP Principle: Fully Local**
- Zero outbound network calls in MVP. All processing — ingestion, extraction, embedding, querying — happens on-device.
- No telemetry, no update checks, no auth in MVP. Single-user local tool.
- Future features (web scraping, registry lookups, external data enrichment) will introduce controlled outbound calls — these are the *only* acceptable network activity, and they are opt-in per action.

### Evidence Integrity

**Document Immutability:**
- Uploaded source documents are stored as-is. The system never modifies, re-encodes, or alters original files.
- All extracted text, entities, relationships, and embeddings are *derived artifacts* — clearly separated from source documents.
- Every derived fact maintains a provenance chain: fact → extracted from chunk → chunk belongs to document → original file on disk.

**Knowledge Base Persistence:**
- All data is persisted permanently. Investigations build a cumulative knowledge base across documents and sessions.
- No automatic expiration or cleanup. Entities and relationships accumulate across investigations, enabling cross-investigation discovery.
- Deletion is explicit and user-initiated only.

### Grounding & Hallucination Prevention

**GRAPH FIRST — Non-Negotiable Principle:**
- The knowledge graph is the single source of truth. If a fact isn't in the graph with a traceable source citation, it does not exist.
- The LLM's role is strictly:
  1. **Query translation** — natural language → Cypher/vector search
  2. **Result presentation** — graph results → human-readable answer with citations
- The LLM **never** infers, speculates, or fills gaps. No "likely" connections. No "possibly related." No hedged guesses.
- Every fact in every answer must resolve to: entity/relationship → source chunk → source document → page/passage.
- If the graph cannot answer a question, the system says "No connection found in your documents" — not a fabricated answer.

**Confidence & Transparency:**
- Entity extraction confidence scores are stored and surfaceable.
- Relationship evidence strength is trackable (single source vs. corroborated across multiple documents).
- Users can always inspect *why* the system believes a connection exists.

### Operational Security

**Deferred to post-MVP.** Future considerations include:
- Application disguise/stealth mode
- Encrypted storage at rest
- Secure deletion (wiping database journals, vector indices, filesystem traces)
- Plausible deniability features for at-risk journalists

### Domain Risk Mitigations

| Risk | Impact | MVP Mitigation |
|------|--------|---------------|
| LLM hallucination in answers | Defamation, false accusations, blown investigations | GRAPH FIRST: no fact without source citation. LLM translates, never generates. |
| Document tampering accusation | Evidence thrown out, credibility destroyed | Immutable source storage. Derived artifacts clearly separated. |
| Data leak via network call | Source exposure, whistleblower danger | Zero outbound calls in MVP. Fully local stack. |
| Entity extraction errors | Wrong connections, missed connections | Confidence scoring per entity. Users can inspect extracted text. |
| Knowledge base corruption | Lost investigation progress | Persistent storage. PostgreSQL + Neo4j durability guarantees. |

## Innovation & Novel Patterns

### Detected Innovation Areas

**1. GRAPH FIRST Grounding Architecture**
Existing GraphRAG implementations (Microsoft GraphRAG, LightRAG) use the graph to enhance LLM responses — the LLM remains the synthesizer and can still hallucinate. OSINT inverts this: the graph is the sole authority, and the LLM is restricted to query translation and result presentation. This isn't a tuning parameter; it's a hard architectural constraint. The result is answers that are provably grounded in source documents — a requirement for journalism and law enforcement that no existing open-source GraphRAG system enforces.

**2. Privacy-by-Architecture**
Privacy in OSINT isn't a policy or a toggle — it's the architecture itself. Zero outbound network calls, local LLMs, local databases, local storage. The privacy guarantee is verifiable by inspecting the Docker Compose file and network traffic. This is a categorically different claim than "we encrypt your data" or "we don't share with third parties."

**3. Cross-Investigation Knowledge Accumulation**
Investigations don't exist in isolation. Entities and relationships persist across investigations, building a cumulative knowledge base. A person who appears in Investigation A may surface unexpected connections when documents from Investigation B are ingested months later. This transforms OSINT from a single-use analysis tool into a persistent investigative memory — a capability previously limited to enterprise intelligence platforms.

**4. Democratized Intelligence Analysis via Local LLMs**
The convergence of capable local LLMs (Qwen 2.5 7B), efficient graph databases (Neo4j), and vector search (Qdrant) — all runnable on consumer hardware — makes enterprise-grade investigation tooling accessible for the first time without cloud dependencies or enterprise budgets.

### Market Context & Competitive Landscape

| Solution | Approach | OSINT Differentiator |
|----------|----------|---------------------|
| Microsoft GraphRAG | Cloud LLMs, LLM-first synthesis, research-oriented | GRAPH FIRST grounding, local-only, investigation-focused UX |
| LightRAG | Lightweight GraphRAG, cloud LLMs | Local LLMs, evidence chains, persistent knowledge base |
| Maltego | Graph analysis, cloud transforms, enterprise pricing | Free, local-first, natural language queries, auto-extraction |
| i2 Analyst's Notebook | Manual graph building, enterprise licensing | Automatic extraction, accessible pricing (free), local LLMs |
| Palantir | Enterprise intelligence platform, government contracts | Consumer hardware, open source, journalist-accessible |

OSINT doesn't compete with these directly — it occupies an unserved niche: powerful investigation tooling for users who can't afford enterprise tools and can't trust cloud services.

### Validation Approach

| Innovation | Validation Method | Success Criteria |
|------------|------------------|-----------------|
| GRAPH FIRST grounding | Test with known-answer document sets; verify zero hallucinated facts in answers | 100% of facts in answers traceable to source documents |
| Local LLM extraction quality | Benchmark Qwen 2.5 7B against corruption-domain test corpus | >80% entity extraction precision |
| Cross-investigation discovery | Seed two related investigations; verify cross-investigation entity linking | System surfaces connections between separately-uploaded document sets |
| Consumer hardware viability | Performance benchmarks on minimum spec (16GB RAM, 8GB VRAM) | Full pipeline operational within defined performance targets |

### Innovation Risk Mitigation

See [Risk Mitigation Strategy](#risk-mitigation-strategy) for comprehensive risk analysis. Key innovation-specific fallbacks:
- **Model quality:** Architecture is model-agnostic via Ollama — swap Qwen 2.5 7B for Mistral/Llama 3 without code changes
- **GRAPH FIRST too restrictive:** Add explicit "speculative mode" toggle in v2+ with clear labeling — never mix with grounded facts
- **Cross-investigation false positives:** Context-based entity disambiguation + confidence scoring (deferred to v1.1)

## Web App Specific Requirements

### Project-Type Overview

OSINT is a local-first single-page application (Next.js + React) accessed via browser at `localhost`. It is not a public-facing website — it runs against a local Docker Compose stack. This fundamentally changes typical web app concerns: no SEO, no CDN, no multi-device responsiveness, no public accessibility compliance for MVP.

### Technical Architecture Considerations

**Application Type:** SPA (Single-Page Application)
- Next.js 14 with React, tRPC for type-safe API communication
- Cytoscape.js for interactive graph visualization
- Tailwind CSS + shadcn/ui for component library

**Browser Support:**
- Modern browsers only: Chrome, Firefox, Safari (latest versions)
- Minimum viewport: 1280px width (laptop/desktop)
- No mobile or tablet support required

**SEO:** Not applicable — localhost application

**Accessibility:** Deferred to post-MVP. Future versions should support keyboard navigation of graph, screen reader compatibility for Q&A results, and high-contrast mode.

### Real-Time Communication

**Requirement: Live processing updates via push**
- Server-Sent Events (SSE) from Python worker → Next.js frontend
- Use cases:
  - Document processing progress (per-document status: queued → extracting text → extracting entities → embedding → complete)
  - Entity extraction results appearing in real-time as documents process
  - Query processing status (translating → searching graph → synthesizing answer)
- Architecture: Redis pub/sub as message broker between Celery worker and Next.js API, SSE from API to browser
- SSE chosen over WebSocket: simpler (unidirectional, auto-reconnect built into browsers), sufficient since frontend only receives updates

### Resilience & Error Handling

**Graceful Ollama failure handling:**
- Frontend monitors backend health via heartbeat or SSE connection state
- If Ollama crashes mid-processing:
  - In-progress document marked as "failed — retry available"
  - Already-processed documents and their entities remain intact in Neo4j/Qdrant
  - User sees clear status: "Processing paused — LLM service unavailable. Retrying..."
  - Auto-retry when Ollama comes back online, or manual retry per document
- If Ollama is unavailable at query time:
  - Graph browsing and visualization still work (Neo4j is independent)
  - Natural language queries return: "LLM service unavailable — try again shortly"
  - Direct graph exploration remains fully functional

**Service dependency matrix:**

| Service Down | Impact | Graceful Behavior |
|-------------|--------|-------------------|
| Ollama | No extraction, no NL queries | Graph browsing works. Clear error. Auto-retry on recovery. |
| Neo4j | No graph queries, no visualization | Document upload still queues. Error on graph pages. |
| Qdrant | No semantic search | Graph queries work. NL queries fall back to graph-only. |
| Redis | No job queue, no real-time updates | Frontend shows stale state. Manual refresh. |
| PostgreSQL | No metadata | Application unavailable. Clear error. |

### Graph Visualization Architecture

**Requirement: Dynamic loading for unbounded graph size**
- Graph can be any size — no artificial upper limit on nodes or relationships
- Implementation approach:
  - **Viewport-based loading:** Load and render only nodes visible in current viewport + one level of neighbors
  - **Progressive disclosure:** Start with high-connectivity hub nodes; expand on click/zoom
  - **Search-to-graph:** Query results highlight a subgraph; user expands from there
  - **Level-of-detail:** Zoomed out shows clusters; zoomed in shows individual nodes with labels
- Cytoscape.js performance considerations:
  - Smooth interaction up to ~500 visible nodes at once
  - Beyond 500: switch to WebGL renderer or cluster representation
  - Node/edge data fetched on demand from Neo4j, not preloaded

**Graph interaction patterns:**
- Click node → show entity detail card
- Click edge → show relationship with source citation
- Double-click node → expand neighborhood (load connected nodes)
- Search → highlight matching nodes and shortest paths
- Filter by entity type (people, organizations, locations)
- Filter by source document

### Implementation Considerations

**Performance Targets (Frontend):**

| Metric | Target |
|--------|--------|
| Initial page load | <3 seconds |
| Graph render (up to 500 nodes) | <2 seconds |
| Node expand (load neighbors) | <1 second |
| Query result display | Streaming as available |
| Document upload feedback | Immediate (before processing starts) |

**State Management:**
- Investigation state persisted server-side (PostgreSQL)
- Frontend state is ephemeral — refresh returns to last investigation view
- No client-side caching of sensitive document content

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Problem-Solving MVP — prove the core pipeline works on real investigation documents.

**Core Hypothesis:** A local GraphRAG system can extract entities from corruption-domain PDFs with sufficient accuracy to surface hidden connections that investigators couldn't find manually, with every fact provably grounded in source documents.

**Resource Requirements:** Solo developer with Claude Code assistance. All infrastructure containerized via Docker Compose. Zero external service dependencies.

**Scope Decision: No Auth for MVP.** This is a single-user local tool. Authentication solves a problem that doesn't exist until multi-user and knowledge base exchange are introduced in v2. Removing auth eliminates network call dependencies and simplifies the stack.

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**
- Journey 1 (Maria Success Path) — full support
- Journey 2 (Maria Edge Case) — partial support (confidence indicators, graceful degradation)
- Journey 4 (Admin Setup) — full support

**Must-Have Capabilities:**

| Capability | Rationale |
|-----------|-----------|
| Bulk PDF upload with progress (SSE) | Entry point for all investigations |
| PDF text extraction (PyMuPDF) | Foundation for everything downstream |
| Entity extraction via Ollama (Qwen 2.5 7B) — people, organizations, locations | Core value: automated connection discovery |
| Relationship detection (WORKS_FOR, KNOWS, LOCATED_AT, MENTIONED_IN) | Graph structure that enables queries |
| Neo4j knowledge graph storage | Persistent, queryable relationship store |
| Qdrant vector embeddings (nomic-embed-text) | Semantic search for natural language queries |
| Natural language Q&A with GRAPH FIRST grounding | The "aha" moment — ask a question, get a cited answer |
| Source citations with click-through to original passage | Trust mechanism — every fact is verifiable |
| Interactive graph visualization (Cytoscape.js) with dynamic loading | Visual exploration of entity networks |
| Entity detail cards with relationships and sources | Deep inspection of individual entities |
| Confidence indicators per document/entity | Tells users which results to trust |
| Investigation CRUD (create, list, delete) | Basic workspace management |
| Docker Compose single-command deployment | Accessible setup for technical users |
| Service health checks and model readiness detection | Prevents broken first-run experience |
| Graceful Ollama crash handling with auto-retry | Resilience for long processing jobs |

**Explicitly NOT in MVP:**

| Feature | Rationale | Target |
|---------|-----------|--------|
| Authentication | Single-user local tool. No auth needed. | v2 |
| Image OCR (Tesseract + moondream2) | PDF-only proves core hypothesis | v1.1 |
| Manual entity merge/correction | Workaround: manual notes. Polish feature. | v1.1 |
| Web page ingestion | PDFs solve core problem | v1.1 |
| Multi-user collaboration | Primary user works solo | v2 |
| Knowledge base exchange | Requires auth + networking | v2 |
| External data integrations | Enrichment, not core | v2 |
| Export formats | Screenshot/copy works for MVP | v2 |
| Cross-investigation entity linking | Requires entity disambiguation. Data persists, queries come later. | v1.1 |
| Operational security features | Important but not validation-blocking | v2+ |
| Accessibility (WCAG) | 5 beta users, not public release | v2+ |

### Post-MVP Features

**Phase 2 — v1.1 (Input Expansion & Polish):**
- Image OCR (Tesseract + moondream2)
- Manual entity creation, correction, and merge
- Web page ingestion (URL capture)
- Processed text preview per document
- Cross-investigation entity linking and knowledge accumulation queries
- Improved entity disambiguation

**Phase 3 — v2 (Collaboration & Enrichment):**
- Authentication and user accounts
- Knowledge base exchange between trusted investigators
- Multi-user collaboration for newsroom teams
- External data integrations (OpenSanctions, WHOIS, Wayback Machine)
- Export formats (PDF reports, structured evidence chains, JSON/CSV)
- Browser extension for web capture
- Evidence chain export for law enforcement
- Chain-of-custody metadata

**Phase 4 — v3+ (Intelligence Platform):**
- Real-time feed monitoring
- Advanced entity types (hypotheses, evidence gaps, patterns)
- Counter-hypothesis query mode
- Blockchain/financial trail analysis
- Encrypted sharing between investigators
- Operational security features (stealth mode, secure deletion)
- Maltego/i2 export compatibility

### Risk Mitigation Strategy

**Technical Risks:**

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Entity extraction quality <80% | Medium | Critical — entire product fails | Model-agnostic via Ollama. Swap to Mistral/Llama 3. Tune prompts. Fall back to smaller focused models per entity type. |
| Consumer hardware too slow | Low | High — blocks adoption | Optimize chunking, batch sizes. Async processing with queue. Document minimum hardware clearly. |
| Dynamic graph loading complexity | Medium | Medium — delays MVP | Start with "load top 200 hub nodes, click to expand." Iterate. Time-box to 2 weeks. |
| Cross-investigation entity linking false positives | Medium | Medium — erodes trust | Deferred to v1.1. Per-investigation graphs in MVP. |

**Market Risks:**

| Risk | Mitigation |
|------|------------|
| Target users not technical enough for Docker setup | One-line install script. README with screenshots. Future: packaged desktop app. |
| Competing open-source GraphRAG projects move faster | Differentiate on GRAPH FIRST grounding + investigation UX, not GraphRAG technology. |
| Grant funding doesn't materialize | Zero operational costs. Community contribution model. |

**Resource Risks:**

| Risk | Mitigation |
|------|------------|
| Solo developer burnout | Tight MVP scope. 8-week timeline. Ship smallest useful thing first. |
| Scope creep mid-development | This PRD is the contract. Features not in MVP don't exist until MVP ships. |

## Functional Requirements

### Investigation Management

- **FR1:** Investigator can create a new investigation with a name and description
- **FR2:** Investigator can view a list of all their investigations
- **FR3:** Investigator can delete an investigation and all its associated data
- **FR4:** Investigator can open an investigation to view its documents, entities, and graph

### Document Ingestion

- **FR5:** Investigator can upload multiple PDF files simultaneously to an investigation
- **FR6:** Investigator can drag and drop a folder of PDFs into the upload area
- **FR7:** System extracts text content from uploaded PDF documents
- **FR8:** System stores original uploaded documents immutably (never modified)
- **FR9:** Investigator can view the list of documents in an investigation with processing status
- **FR10:** Investigator can view the extracted text of a processed document

### Entity Extraction & Knowledge Graph

- **FR11:** System automatically extracts people, organizations, and locations from document text using local LLM
- **FR12:** System automatically detects relationships between extracted entities (WORKS_FOR, KNOWS, LOCATED_AT, MENTIONED_IN)
- **FR13:** System stores extracted entities and relationships in a knowledge graph
- **FR14:** System assigns confidence scores to extracted entities and relationships
- **FR15:** System maintains provenance chain for every extracted fact (entity → chunk → document → page/passage)
- **FR16:** System generates vector embeddings for document chunks and stores them for semantic search

### Natural Language Query & Answer

- **FR17:** Investigator can ask natural language questions about their investigation
- **FR18:** System translates natural language queries into graph and vector search operations
- **FR19:** System returns answers grounded exclusively in knowledge graph data (GRAPH FIRST — no hallucinated facts)
- **FR20:** Every fact in an answer includes a source citation linking to the original document passage
- **FR21:** Investigator can click a citation to view the original source passage in context
- **FR22:** System reports "No connection found in your documents" when the graph cannot answer a question

### Graph Visualization

- **FR23:** Investigator can view an interactive graph of entities and relationships in their investigation
- **FR24:** System dynamically loads graph nodes on demand (no upper limit on graph size)
- **FR25:** Investigator can click a node to view an entity detail card with properties, relationships, and source documents
- **FR26:** Investigator can click an edge to view relationship details with source citation
- **FR27:** Investigator can expand a node's neighborhood by interacting with it (load connected entities)
- **FR28:** Investigator can filter the graph by entity type (people, organizations, locations)
- **FR29:** Investigator can filter the graph by source document
- **FR30:** Investigator can search for entities and see matching nodes highlighted in the graph

### Processing Pipeline & Feedback

- **FR31:** System processes uploaded documents asynchronously via a job queue
- **FR32:** Investigator receives real-time progress updates during document processing (per-document status)
- **FR33:** System displays per-document processing status (queued, extracting text, extracting entities, embedding, complete, failed)
- **FR34:** Investigator can view processing results as they arrive (entities appearing while other documents still process)

### Resilience & Error Handling

- **FR35:** System marks documents as "failed — retry available" when processing fails mid-extraction
- **FR36:** System automatically retries failed documents when the LLM service recovers
- **FR37:** Investigator can manually trigger retry for failed documents
- **FR38:** System preserves all successfully processed data when a service fails (no data loss from partial failures)
- **FR39:** System provides graph browsing and visualization when the LLM service is unavailable (degraded mode)
- **FR40:** System displays clear service status to the investigator (which services are operational)

### Deployment & Setup

- **FR41:** Administrator can deploy the complete system with a single Docker Compose command
- **FR42:** System provides health check endpoints for all services
- **FR43:** System detects and reports LLM model readiness before allowing queries
- **FR44:** System displays clear error messages when hardware requirements are insufficient

### Confidence & Transparency

- **FR45:** Investigator can view confidence indicators for each processed document (extraction quality)
- **FR46:** Investigator can view confidence scores for individual entities
- **FR47:** Investigator can inspect the evidence supporting any relationship (which documents, which passages)

## Non-Functional Requirements

### Performance

**Document Processing Pipeline:**
- NFR1: 100-page PDF fully processed (text extraction + entity extraction + embedding) in <15 minutes on minimum hardware (16GB RAM, 8GB VRAM)
- NFR2: Individual document text extraction completes in <30 seconds per 100 pages
- NFR3: Processing pipeline handles bulk upload of 50+ documents without queue failure or memory exhaustion
- NFR4: Real-time progress updates (SSE) delivered to frontend within 1 second of processing state change

**Query & Response:**
- NFR5: Natural language question returns answer with citations in <30 seconds on minimum hardware
- NFR6: Graph path queries (shortest path between two entities) return in <10 seconds
- NFR7: Query streaming begins within 5 seconds (progressive response, not all-or-nothing)

**Frontend Responsiveness:**
- NFR8: Initial application load in <3 seconds
- NFR9: Graph visualization renders up to 500 visible nodes in <2 seconds
- NFR10: Node neighborhood expansion (click to load connected entities) completes in <1 second
- NFR11: Entity search returns results in <500 milliseconds

**Hardware Baseline:**
- NFR12: All performance targets measured against minimum spec: 16GB RAM, 8GB VRAM (RTX 3060/4060 or M1/M2 Mac with 16GB unified), 50GB SSD
- NFR13: UI interactions (navigation, graph browsing) respond in <500ms while document processing is active

### Security & Privacy

**Data Sovereignty:**
- NFR14: Zero outbound network connections during normal operation (document processing, querying, graph browsing)
- NFR15: All LLM inference executes locally via Ollama — no external API calls under any circumstances
- NFR16: No telemetry, analytics, crash reporting, or update checking that contacts external servers
- NFR17: System is fully operational on an air-gapped network (no internet required after initial setup and model download)

**Document Integrity:**
- NFR18: Original uploaded documents are stored byte-for-byte identical to the uploaded file (verified by checksum)
- NFR19: System never modifies, re-encodes, compresses, or alters source documents
- NFR20: Derived data (extracted text, entities, relationships, embeddings) is stored separately from source documents with clear provenance

**Grounding Guarantee:**
- NFR21: 100% of facts presented in query answers are traceable to a specific source document passage — zero tolerance for ungrounded assertions
- NFR22: System never presents LLM-generated speculation, inference, or "likely" connections as facts

### Reliability & Data Integrity

**Data Persistence:**
- NFR23: All investigation data (documents, entities, relationships, embeddings) persists across application restarts, Docker restarts, and system reboots
- NFR24: No data loss from partial processing failures — successfully processed documents remain intact when later documents fail
- NFR25: Database transactions are atomic — no partially-written entities or relationships

**Service Resilience:**
- NFR26: Individual service failure (Ollama, Neo4j, Qdrant) does not crash the entire application — degraded functionality rather than total failure
- NFR27: Application recovers automatically when failed services come back online without requiring full restart
- NFR28: Processing queue survives Ollama restarts — pending jobs resume, not lost

**Deployment Reliability:**
- NFR29: Docker Compose deployment succeeds on first attempt on supported platforms (Linux, macOS with Docker Desktop) with documented prerequisites
- NFR30: System provides clear, actionable error messages when deployment fails (insufficient memory, port conflicts, missing GPU drivers)
