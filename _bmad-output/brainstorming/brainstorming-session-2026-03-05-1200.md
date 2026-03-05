---
stepsCompleted: [1, 2, 3, 4]
inputDocuments: []
session_topic: 'GraphRAG system for multi-source investigations - connecting people, companies, events across diverse data types'
session_goals: 'Technical architecture, novel features, data modeling, UX concepts, integration strategies'
selected_approach: 'ai-recommended'
techniques_used: ['Morphological Analysis']
ideas_generated: 100+
technique_execution_complete: true
session_active: false
workflow_completed: true
context_file: ''
---

# Brainstorming Session Results

**Facilitator:** Gennadiy
**Date:** 2026-03-05
**Duration:** ~60 minutes
**Technique:** Morphological Analysis (AI-Recommended)

---

## Session Overview

**Topic:** GraphRAG system for multi-source investigations - connecting people, companies, events across diverse data types

**Goals:** Technical architecture, novel features, data modeling, UX concepts, integration strategies

### Use Cases
- Journalism/OSINT research
- Law enforcement investigations
- Corporate due diligence

### Technical Constraints
- TypeScript + Python stack
- Solo developer with Claude Code assistance
- Multi-modal input: PDFs, images, web links, Office docs, maps
- **Local LLM** (Ollama) for privacy and zero API costs
- **Neo4j** for native graph queries
- **Qdrant** for vector search

---

## Complete Idea Inventory

### Parameter 1: Input Source Types (24+ options)

**Core Document Types:**
- PDFs
- Images (JPG/PNG/TIFF/HEIC)
- Web pages
- Word docs
- Excel spreadsheets
- PowerPoint
- Maps/GIS data
- Audio recordings
- Video files
- Real-time social feeds
- Structured databases
- Dark/deep web archives

**Advanced Investigation Sources:**
- Email exports (PST/MBOX/EML)
- Chat logs (Slack/Teams/WhatsApp/Telegram)
- Calendar files (ICS)
- Financial documents (statements, invoices, crypto)
- Travel records
- Phone records (CDR)
- Blockchain/wallet data
- Satellite imagery
- Vessel/flight tracking (AIS/ADS-B)
- Code repositories
- Handwritten notes (OCR)
- Social graph exports
- Regulatory filings (SEC, Companies House, offshore)

**MVP Scope:** PDF, Images (with OCR), Web URLs only

---

### Parameter 2: Entity Types (16+ options)

**Core Entities:**
- People (+ aliases, roles)
- Organizations
- Events
- Locations

**Extended Entities:**
- Assets (vehicles, properties, vessels, aircraft, artwork)
- Financial Instruments (accounts, wallets, shells, trusts)
- Documents (as first-class entities)
- Communications
- Claims/Statements
- Time Periods
- Projects/Operations
- Identifiers (phones, emails, IDs)

**Abstract/Meta Entities:**
- Patterns (recurring behaviors)
- Hypotheses (investigator theories)
- Evidence Strength indicators
- Gaps/Unknowns

**Novelty:** Treating abstract concepts (hypotheses, gaps, patterns) as graph nodes enables meta-investigation capabilities

**MVP Scope:** People, Organizations, Locations only

---

### Parameter 3: Relationship Types (35+ edge types)

**Core Investigation Edges:**
- WORKS_FOR, KNOWS, OWNS, CONTROLS, FORMERLY_ASSOCIATED, ALLEGEDLY_CONNECTED, COMMUNICATED_WITH, PRESENT_AT, CONTRADICTS, FUNDED_BY, PAID_TO, INTRODUCED_BY, BENEFITS_FROM

**Temporal/Causal Relationships:**
- PRECEDED, ENABLED, TRIGGERED, PREVENTED, COINCIDED_WITH

**Behavioral Pattern Edges:**
- MIMICS_PATTERN_OF, BREAKS_PATTERN, ESCALATED_TO, DISTANCED_FROM

**Network Position Edges:**
- BRIDGES, GATEKEEPS, ISOLATES, FRONTS_FOR

**Evidentiary Meta-Edges:**
- CORROBORATES, REFUTES, SUPERSEDES, EXTRACTED_FROM, CONFIDENCE_LEVEL, LEGALLY_ADMISSIBLE

**Smoking Gun Edges:**
- USED_SAME_DEVICE, SHARED_PROFESSIONAL, CO_BENEFICIARY, TRAVELED_TOGETHER, WARNED, RECRUITED, IMPERSONATED

**Novelty:** Enables queries like "show me all BRIDGES who DISTANCED_FROM cluster after EVENT"

**MVP Scope:** WORKS_FOR, KNOWS, LOCATED_AT, MENTIONED_IN

---

### Parameter 4: Query Types (18+ patterns)

**Basic Patterns:**
- Entity lookup
- Simple connections
- Date filtering

**Investigation-Grade Queries:**
- Path Finding ("How is A connected to B?")
- Temporal Sequence ("What happened before X?")
- Pattern Matching ("Find similar behavior to Bad Actor")
- Cluster Detection ("Show groups operating together")
- Anomaly Queries ("What doesn't fit?")
- Gap Analysis ("What's missing?")
- Hypothesis Testing ("If X is true, what else should we see?")
- Counter-Hypothesis ("What contradicts my theory?")
- Provenance Queries ("Where did this fact come from?")
- Diff/Change Queries ("What changed between versions?")

**Natural Language Examples:**
- "Who benefits from this deal?"
- "Show me the money trail"
- "When did they first connect?"
- "What's the weakest link in this chain?"
- "Give me the prosecutable facts"

**Novelty:** Counter-hypothesis queries actively challenge investigator assumptions - combats confirmation bias

**MVP Scope:** "Who is X?", "How connected?", Simple path finding

---

### Parameter 5: Output & Visualization Types (24+ formats)

**Interactive Outputs:**
- Interactive Graph Canvas
- Timeline/Chronology
- Geographic Map Overlay
- Relationship Matrix
- Evidence Board (virtual cork-board)
- Sankey/Flow Diagram
- Hierarchical Org Chart
- Comparison View
- Audit Trail View

**AI-Augmented Outputs:**
- Narrative Summary (LLM-generated)
- Key Findings Highlights
- Confidence Dashboard
- Recommended Next Steps
- Counter-Evidence Panel
- Gap Report
- Risk Assessment
- Witness/Interview Guide

**Export Formats:**
- PDF Report
- Interactive HTML
- Structured Data (JSON/CSV)
- Graph Export (GEXF/GraphML)
- Presentation Deck
- Encrypted Package

**Novelty:** Counter-Evidence Panel and Gap Report actively fight confirmation bias

**MVP Scope:** Basic graph viz, Entity cards, Source citations

---

### Parameter 6: Processing Pipeline Architecture

**Final Architecture Decision: Pattern B with Local LLM**

```
┌─────────────────────────────────────────────────────────────────┐
│                    MVP Architecture                              │
│                                                                  │
│   ┌─────────────────────┐         ┌─────────────────────┐       │
│   │   Python Worker     │   Queue │   TypeScript API    │       │
│   │   (FastAPI + Celery)│◄───────►│   (Next.js API)     │       │
│   ├─────────────────────┤  Redis  ├─────────────────────┤       │
│   │ • PDF extraction    │         │ • Auth (Clerk)      │       │
│   │ • Ollama NER        │         │ • File upload       │       │
│   │ • Local embeddings  │         │ • REST/tRPC         │       │
│   │ • Neo4j writes      │         │ • Query interface   │       │
│   └──────────┬──────────┘         └──────────┬──────────┘       │
│              │                               │                   │
│              ▼                               ▼                   │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │                      Ollama                               │  │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │  │
│   │  │  Qwen 2.5   │  │  nomic-     │  │   moondream2    │   │  │
│   │  │    7B       │  │  embed-text │  │   (Vision)      │   │  │
│   │  │  (NER/RAG)  │  │  (768 dim)  │  │                 │   │  │
│   │  └─────────────┘  └─────────────┘  └─────────────────┘   │  │
│   └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │                    Data Layer                             │  │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │  │
│   │  │   Neo4j     │  │   Qdrant    │  │   PostgreSQL    │   │  │
│   │  │  (Graph)    │  │  (Vectors)  │  │   (Metadata)    │   │  │
│   │  └─────────────┘  └─────────────┘  └─────────────────┘   │  │
│   └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │              Next.js Frontend                             │  │
│   │         (React + Cytoscape.js for graphs)                │  │
│   └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Technology Stack:**

| Layer | Technology |
|-------|------------|
| **LLM** | Ollama + Qwen 2.5 7B |
| **Embeddings** | nomic-embed-text (768 dim) |
| **Vision/OCR** | moondream2 + Tesseract |
| **Graph DB** | Neo4j 5 |
| **Vector DB** | Qdrant |
| **Relational** | PostgreSQL 16 |
| **Queue** | Redis + Celery |
| **Backend** | FastAPI (Python) |
| **Frontend** | Next.js 14 + tRPC |
| **Auth** | Clerk |
| **Graph Viz** | Cytoscape.js |
| **Styling** | Tailwind + shadcn/ui |

**Hardware Requirements (Minimum):**
- RAM: 16GB
- GPU: 8GB VRAM (RTX 3060/4060) or M1/M2 Mac with 16GB
- Storage: 50GB SSD

---

### Parameter 7: Integrations & External Systems (50+ options)

**Data Source Integrations:**
- Company Registries: OpenCorporates, Companies House, SEC EDGAR, OpenOwnership
- People/Identity: Pipl, FullContact, Hunter.io
- Sanctions/Risk: OpenSanctions, OFAC, World-Check
- News/Media: GDELT, NewsAPI, Event Registry
- Public Records: PACER, Property registries
- Social/OSINT: Twitter/X, Reddit, Telegram, Archive.org
- Financial: OpenPayments, IRS 990s
- Geospatial: OpenStreetMap, Google Places, Mapbox
- Domain/Web: WHOIS, BuiltWith, Wayback Machine
- Crypto/Blockchain: Etherscan, Chainalysis, Arkham

**Workflow Integrations:**
- Obsidian, Notion (PKM)
- Slack, Discord (alerts)
- Google Drive, Dropbox (file sync)
- Browser Extension (capture)

**Export Targets:**
- Maltego, Gephi, Neo4j, i2 Analyst Notebook
- Google Earth (KML), Timeline JS
- PDF/Word reports

**Free Integration Gold:**
- OpenSanctions (sanctions screening)
- Wayback Machine (historical snapshots)
- WHOIS/RDAP (domain ownership)
- SEC EDGAR (US public companies)
- Companies House (UK companies)
- Wikidata (entity linking)

**MVP Integration Priorities:**
- P0: Local Ollama, S3/R2, Clerk
- P1: OpenSanctions, WHOIS, Wayback Machine
- P2: OpenCorporates, News APIs, Browser extension
- P3: Maltego export, Blockchain APIs

---

## Idea Organization and Prioritization

### Thematic Organization

| Theme | Ideas | Key Insight |
|-------|-------|-------------|
| **Data Ingestion** | 24+ input types | Investigation data is radically heterogeneous |
| **Entity Modeling** | 16+ entity types | Abstract entities (hypotheses, gaps) enable meta-investigation |
| **Relationships** | 35+ edge types | Edge richness drives graph power |
| **Queries** | 18+ patterns | Counter-hypothesis queries fight confirmation bias |
| **Outputs** | 24+ formats | Different questions need different views |
| **Architecture** | Pattern B + Local LLM | Privacy + zero API cost + native graph/vector |
| **Integrations** | 50+ systems | Rich free ecosystem available |

### Prioritization Results

**Top Priority Ideas:**
1. Pattern B Architecture with Neo4j + Qdrant + Ollama
2. Local LLM entity extraction (Qwen 2.5 7B)
3. Basic graph viz with source citations

**Quick Win Opportunities:**
1. PDF upload + text extraction (PyMuPDF)
2. Basic entity storage in Neo4j
3. Cytoscape.js graph rendering

**Breakthrough Concepts (v2+):**
1. Hypothesis/Gap as first-class graph entities
2. Counter-hypothesis query mode
3. Witness Interview Guide generation from graph

---

## Action Plan: MVP Implementation

### Phase 1: Foundation (Weeks 1-2)

| Task | Deliverable |
|------|-------------|
| Set up monorepo | `/apps/api` (Next.js), `/apps/worker` (Python) |
| Docker compose | Postgres + Neo4j + Qdrant + Redis + Ollama |
| Pull Ollama models | qwen2.5:7b, nomic-embed-text, moondream |
| Clerk auth | Protected routes, user sessions |
| S3/R2 file upload | Store documents, return URLs |
| Neo4j connection | Python + TS drivers |
| Qdrant collection | 768-dim vectors for nomic-embed-text |
| Basic investigation CRUD | Create, list, delete |

**Success Indicator:** Can create investigation and upload file

### Phase 2: Extraction Pipeline (Weeks 3-4)

| Task | Deliverable |
|------|-------------|
| PDF text extraction | PyMuPDF → raw text + metadata |
| Text chunking | ~500 token chunks with overlap |
| Ollama entity extraction | Qwen 2.5 extracts people, orgs, locations |
| Ollama embeddings | nomic-embed-text for chunks |
| Qdrant indexing | Store chunks with vectors |
| Neo4j entity nodes | Create Entity nodes with properties |
| Neo4j relationships | Create typed edges with evidence |

**Success Indicator:** Upload PDF → see entities in Neo4j

### Phase 3: Query & Display (Weeks 5-6)

| Task | Deliverable |
|------|-------------|
| Qdrant semantic search | RAG retrieval for questions |
| Neo4j path queries | Cypher pathfinding |
| Neo4j neighborhood queries | Entity + connections |
| Ollama answer synthesis | Combine graph + chunks → answer |
| Entity detail page | Card with properties + relationships |
| Graph visualization | Cytoscape.js network view |
| Source citations | Click to see original chunk |

**Success Indicator:** Ask question → get visual answer with sources

### Phase 4: Polish & Deploy (Weeks 7-8)

| Task | Deliverable |
|------|-------------|
| Manual entity merge UI | Neo4j node merging |
| Image OCR | Tesseract + moondream2 |
| Error handling | Graceful failures |
| Loading states | Progress indicators |
| Deploy | VPS with Docker Compose or split services |
| Documentation | README, setup guide |

**Success Indicator:** Working deployment, can demo to others

---

## Docker Compose (Complete Local Stack)

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: osint
      POSTGRES_PASSWORD: osint
      POSTGRES_DB: osint
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  neo4j:
    image: neo4j:5
    environment:
      NEO4J_AUTH: neo4j/password
      NEO4J_PLUGINS: '["apoc"]'
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

volumes:
  postgres_data:
  neo4j_data:
  qdrant_data:
  ollama_data:
```

---

## Model Setup Script

```bash
#!/bin/bash
# setup-models.sh

echo "Pulling Ollama models..."

# Main LLM for extraction and synthesis
ollama pull qwen2.5:7b

# Embeddings (768 dimensions)
ollama pull nomic-embed-text

# Vision for images
ollama pull moondream

echo "Models ready!"
ollama list
```

---

## MVP Success Criteria

**"Done" when you can:**

1. ✅ Upload a PDF about corporate corruption
2. ✅ System extracts people, companies, locations (via local Ollama)
3. ✅ See them as nodes in a graph visualization (Neo4j → Cytoscape.js)
4. ✅ Ask "How is Person X connected to Company Y?"
5. ✅ Get answer with source citations (Qdrant RAG + Ollama synthesis)
6. ✅ Click citation to see original document

**That's your MVP. Everything else is v2.**

---

## Session Summary and Insights

### Key Achievements

- **100+ ideas** generated across 7 parameter dimensions
- **Complete architecture** decided: Neo4j + Qdrant + Ollama + Python/TypeScript
- **MVP scope** clearly defined with 8-week roadmap
- **Privacy-first** approach with fully local LLM stack
- **Zero API costs** for LLM operations

### Breakthrough Concepts Discovered

1. **Abstract entities as graph nodes** - Hypotheses, gaps, and patterns become queryable
2. **Counter-hypothesis queries** - Built-in confirmation bias prevention
3. **Edge richness over node count** - Relationship semantics drive investigation power
4. **Local LLM for investigations** - Privacy + cost savings + full control

### Session Reflections

**What Made This Session Valuable:**
- Systematic parameter exploration before any coding
- Architecture decisions documented with rationale
- Clear MVP scope prevents over-engineering
- Solo-dev-friendly patterns throughout
- Privacy considerations shaped technology choices

**Creative Approach:**
- Morphological Analysis proved highly effective for technical systems
- Deep dive on architecture (Parameter 6) yielded concrete implementation path
- Iterative refinement (Postgres → Neo4j+Qdrant → +Local LLM) showed good decision-making

---

## Next Steps

1. **This week:** Set up monorepo structure and Docker Compose
2. **Model setup:** Pull Ollama models (qwen2.5:7b, nomic-embed-text, moondream)
3. **Week 1-2:** Foundation - databases, auth, file upload
4. **Week 3-4:** Extraction pipeline with local Ollama
5. **Week 5-6:** Query interface and graph visualization
6. **Week 7-8:** Polish and deploy

---

**Session Complete.**

*Generated with BMAD Brainstorming Workflow v6.0.4*
