---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - '_bmad-output/brainstorming/brainstorming-session-2026-03-05-1200.md'
date: 2026-03-05
author: Gennadiy
workflow_completed: true
---

# Product Brief: OSINT

## Executive Summary

OSINT is a local-first investigation platform that enables journalists and OSINT researchers to uncover hidden connections in corruption investigations. Users can ask natural language questions like "How is Person X connected to Company Y?" and receive answers with complete source citations and chains of evidence - all without their sensitive data ever leaving their machine.

---

## Core Vision

### Problem Statement

Journalists and OSINT researchers investigating corruption are drowning in documents with no way to connect the dots. They rely on manual notes and spreadsheets that don't scale, can't surface hidden relationships, and fail to maintain the chain of evidence needed for credible reporting.

### Problem Impact

When investigations fail due to tooling limitations, corruption goes unexposed. Months of work leads nowhere. Stories that could hold the powerful accountable never get published. Whistleblowers take risks for nothing.

### Why Existing Solutions Fall Short

Tools like Maltego, i2 Analyst's Notebook, and Palantir exist but fail this audience on two fronts:
- **Cost**: Enterprise pricing excludes underfunded newsrooms and freelance journalists
- **Privacy**: Cloud-based architectures require trusting third parties with explosive, source-identifying material - an unacceptable risk when protecting whistleblowers

### Proposed Solution

A fully local GraphRAG system that ingests documents (PDFs, images, web pages), automatically extracts entities and relationships using local LLMs, and enables natural language queries against a knowledge graph. The magic moment: ask a question, get an answer with every fact traced back to its source document.

### Key Differentiators

1. **Investigator-first UX** - designed for journalists, not data scientists or intelligence analysts
2. **Evidence chains as a first-class feature** - not just connections, but provable, citable, legally-defensible facts
3. **Radically accessible** - zero API costs, runs on consumer hardware, affordable for independent journalists
4. **Privacy by architecture** - local LLMs mean sensitive data never leaves the investigator's machine

---

## Target Users

### Primary Users

**Persona: Maria - Independent Investigative Journalist**

Maria is a staff investigative reporter at a regional newspaper, though she could just as easily be freelance. She covers political corruption and organized crime in her area - stories the big outlets ignore.

- **Context:** Works solo, no technical support, underfunded newsroom
- **Tech comfort:** Needs GUI - comfortable with spreadsheets but not command line. Wants to focus on the story, not the tools
- **Time pressure:** Quick turnaround - can't spend weeks learning a tool
- **Current pain:** Drowning in leaked documents, using spreadsheets to track connections, losing track of where facts came from
- **Privacy need:** Protecting whistleblowers and confidential sources is non-negotiable

**What success looks like:** Maria uploads a folder of leaked PDFs, asks "How is the mayor connected to this construction company?", and gets an answer with citations she can use in her article - all without her source-identifying documents ever leaving her laptop.

### Secondary Users

**Persona: Detective Carlos - Local Police Investigator**

Carlos is a detective working organized crime or public corruption cases at a local police department.

- **Context:** Limited budget, no access to federal tools like Palantir
- **Needs:** Similar to Maria, but with additional chain-of-custody requirements for evidence
- **Privacy need:** Case materials must stay on department systems

**Persona: Analyst Yuki - Intelligence Agency**

Yuki is an analyst at a government intelligence agency handling sensitive material.

- **Context:** Classified information, strict operational security requirements
- **Needs:** Powerful analysis tools, but cloud solutions are categorically forbidden
- **Privacy need:** Data cannot leave agency systems under any circumstances

### User Journey

**Discovery:** Finds OSINT through internet search or OSINT research community

**Onboarding:** Uploads an entire folder of documents on day one - no time for tutorials, needs to hit the ground running

**Core Usage:** Asks natural language questions, explores graph connections, traces facts back to sources

**Success Moment:** Asks a question and gets an actionable answer with citations - the "aha!" that proves the tool works

**Long-term:** OSINT becomes the starting point for every new investigation

---

## Success Metrics

### User Success Metrics

**Primary Success Indicator:** Published investigations citing OSINT-surfaced facts

- **Metric:** Number of published stories where journalists cite facts discovered through OSINT
- **Measurement:** Self-reported through community sharing / "wall of impact" showcase
- **12-Month Target:** 10 published stories

**Leading Indicators:**
- Documents uploaded per investigation
- Questions asked per session
- Return usage (users coming back for new investigations)

### Business Objectives

**Funding Model:** Mission-driven, grant and donation supported

- **Objective:** Secure funding from journalism-focused foundations (Knight Foundation, Mozilla, Ford Foundation, First Look Media)
- **12-Month Target:** One small grant secured
- **Purpose:** Cover infrastructure costs, enable continued development

**Sustainability:** Keep operational costs near zero through local-first architecture (no cloud API costs)

### Key Performance Indicators

| KPI | Target (12 months) | Measurement |
|-----|-------------------|-------------|
| Published stories citing OSINT | 10 | Community self-reporting |
| GitHub stars | 500 | GitHub metrics |
| Grant funding | 1 small grant | Foundation outreach |
| Active community members | 100+ | Discord/forum membership |
| Contributors | 5+ | GitHub contributors |

### North Star Metric

**Corruption exposed through OSINT-enabled journalism**

Every other metric serves this goal. Stars and grants are means to an end - the real success is when OSINT helps journalists hold power accountable.

---

## MVP Scope

### Core Features

**Document Ingestion**
- Bulk PDF upload (entire folders)
- Basic image OCR via Tesseract + moondream2
- Local file storage (S3/R2 compatible)

**Entity Extraction**
- People, Organizations, Locations
- Powered by local Ollama (Qwen 2.5 7B)
- Automatic relationship detection

**Knowledge Graph**
- Neo4j for entity and relationship storage
- Basic relationship types: WORKS_FOR, KNOWS, LOCATED_AT, MENTIONED_IN
- Qdrant for vector embeddings and semantic search

**Natural Language Q&A**
- Ask questions like "How is Person X connected to Company Y?"
- Answers synthesized from graph + document chunks
- Every fact includes source citation

**Visualization**
- Interactive graph view (Cytoscape.js)
- Entity detail cards
- Click-through to source documents

### Out of Scope for MVP

| Feature | Rationale | Target Version |
|---------|-----------|----------------|
| Web scraping / URL ingestion | Adds complexity, PDFs solve core problem | v2 |
| Real-time feeds | Not needed for document-based investigations | v3+ |
| Multi-user collaboration | Primary user (Maria) works solo | v2 |
| Advanced entity types (hypotheses, patterns) | Power feature, not essential for core value | v2+ |
| External integrations (OpenSanctions, WHOIS) | Nice-to-have enrichment, not core | v2 |
| Export formats (PDF reports, Maltego) | Users can screenshot/copy for now | v2 |

### MVP Success Criteria

**Validation Gate:** 5 real users complete a real investigation using OSINT

**"Done" Definition:**
1. Upload a folder of PDFs about a corruption case
2. System extracts people, companies, locations automatically
3. See entities as nodes in interactive graph
4. Ask "How is Person X connected to Company Y?"
5. Get answer with source citations
6. Click citation to view original document passage

**Decision Point:** When 5 users successfully complete investigations, MVP is validated and we proceed to v2.

### Future Vision

**v2 - Expand Input & Collaboration**
- Web page ingestion (URLs, not just files)
- Multi-user collaboration for newsroom teams
- Shared investigations with role-based access

**v3+ - Intelligence Platform**
- Real-time feed monitoring
- External data integrations (OpenSanctions, company registries, WHOIS)
- Advanced entity types (hypotheses, evidence gaps, patterns)
- Export to professional formats (PDF reports, Maltego, i2)
- Counter-hypothesis query mode to fight confirmation bias

**Long-term Vision:** The go-to open-source investigation platform for journalists worldwide - powerful enough for professionals, accessible enough for independents, private enough for anyone handling sensitive material.
