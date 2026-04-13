---
stepsCompleted:
  - step-01-document-discovery
  - step-02-prd-analysis
  - step-03-epic-coverage-validation
  - step-04-ux-alignment
  - step-05-epic-quality-review
  - step-06-final-assessment
workflow_completed: true
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/epics-phase2.md'
  - '_bmad-output/planning-artifacts/ux-design-specification.md'
---

# Implementation Readiness Assessment Report

**Date:** 2026-04-12
**Project:** OSINT
**Scope:** Phase 2 (v1.1 — Input Expansion & Polish)

## PRD Analysis

### Functional Requirements (Phase 2 scope)

FR48: Investigator can upload image files (JPEG, PNG, TIFF) alongside PDFs to an investigation
FR49: System extracts text from image files using Tesseract OCR
FR50: System uses moondream2 (via Ollama) for enhanced image understanding and text extraction from complex/degraded layouts
FR51: System indicates OCR quality confidence per image document (clean scan vs. degraded/handwritten)
FR52: Investigator can manually create a new entity (person, organization, or location) with custom properties and a source annotation
FR53: Investigator can edit/correct an entity's name and properties
FR54: Investigator can merge two or more duplicate entities into a single entity, preserving all relationships and source citations from both
FR55: Investigator can manually create a relationship between two entities with a source annotation
FR56: Investigator can submit a URL to capture a web page as a document source within an investigation
FR57: System downloads, converts (HTML → text), and stores the web page content immutably
FR58: Captured web pages are processed through the same entity extraction and embedding pipeline as PDFs
FR59: System identifies matching entities across different investigations by name, type, and contextual similarity
FR60: Investigator can view cross-investigation entity matches — entities that appear in multiple investigations
FR61: Investigator can query across investigations to find shared entities and relationship patterns
FR62: System detects potential duplicate entities within an investigation and surfaces merge candidates
FR63: System scores merge candidates by confidence (exact match, fuzzy name match, contextual similarity)
FR64: Investigator can review suggested merges and approve or reject each one

**Total FRs: 17 (FR48–FR64)**

### Non-Functional Requirements (Phase 2 scope)

NFR31: OCR processing (Tesseract + moondream2) completes per image page in <60 seconds on minimum hardware (16GB RAM, 8GB VRAM)
NFR32: Web page capture and conversion completes within 30 seconds for standard web pages
NFR33: Cross-investigation entity queries return results within 15 seconds
NFR34: Entity merge operations are atomic — all relationships and source citations transfer completely, or the merge is rolled back with zero data loss

**Total NFRs: 4 (NFR31–NFR34)**

### Additional Requirements

- **Privacy model change:** Web page capture (FR56–FR58) introduces the first outbound network calls. PRD mandates these are opt-in per action only. System never makes automatic/background outbound calls. NFR14 (zero outbound calls) maintained for all other operations.
- **PRD Journey 2 traceability:** Manual entity management (FR52–FR55) directly maps to Maria's v1.1+ wish list from Journey 2 (Edge Case).
- **Innovation risk mitigation:** Entity disambiguation (FR62–FR64) maps to PRD's deferred "context-based entity disambiguation + confidence scoring" for v1.1.
- **Cross-investigation architecture:** PRD notes data persists across investigations and queries come in v1.1. Architecture's single Qdrant collection design was built for this.

### PRD Completeness Assessment

**PRD coverage for Phase 2: ADEQUATE with caveats.**

The PRD defines Phase 2 scope at a feature level (bullet points in Post-MVP section), not at the FR-level detail used for MVP (FR1–FR47). The 17 Phase 2 FRs (FR48–FR64) were derived during epic creation by decomposing the PRD's Phase 2 feature descriptions, user journey wishes, and innovation risk mitigations. This is appropriate — the PRD provides the vision and scope; the epics document formalizes the requirements.

**One gap noted:** The PRD lists "Processed text preview per document" as a Phase 2 feature, but this is arguably already covered by MVP's FR10 ("Investigator can view the extracted text of a processed document") implemented in Story 2.5. The Phase 2 epics do not create a separate FR for this, which is correct — it's enhancement-level work (showing OCR source indicators in the text viewer), addressed within Story 7.3's acceptance criteria.

## Epic Coverage Validation

### Coverage Matrix

| FR | PRD Requirement | Epic | Story | Status |
|----|----------------|------|-------|--------|
| FR48 | Upload image files (JPEG, PNG, TIFF) alongside PDFs | Epic 7 | Story 7.1 | ✅ Covered |
| FR49 | Extract text from image files using Tesseract OCR | Epic 7 | Story 7.1 | ✅ Covered |
| FR50 | moondream2 enhanced image understanding for complex layouts | Epic 7 | Story 7.2 | ✅ Covered |
| FR51 | OCR quality confidence per image document | Epic 7 | Story 7.3 | ✅ Covered |
| FR52 | Manual entity creation with custom properties | Epic 8 | Story 8.1 | ✅ Covered |
| FR53 | Edit/correct entity name and properties | Epic 8 | Story 8.1 | ✅ Covered |
| FR54 | Merge duplicate entities preserving relationships/citations | Epic 8 | Story 8.3 | ✅ Covered |
| FR55 | Manual relationship creation with source annotation | Epic 8 | Story 8.2 | ✅ Covered |
| FR56 | Submit URL to capture web page as document | Epic 9 | Story 9.1 | ✅ Covered |
| FR57 | Download, convert (HTML → text), store web page immutably | Epic 9 | Story 9.1 | ✅ Covered |
| FR58 | Web pages through entity extraction and embedding pipeline | Epic 9 | Story 9.2 | ✅ Covered |
| FR59 | Cross-investigation entity matching by name, type, similarity | Epic 10 | Story 10.1 | ✅ Covered |
| FR60 | View cross-investigation entity matches | Epic 10 | Story 10.2 | ✅ Covered |
| FR61 | Query across investigations for shared entities/patterns | Epic 10 | Story 10.2 | ✅ Covered |
| FR62 | Detect duplicate entities within investigation | Epic 8 | Story 8.4 | ✅ Covered |
| FR63 | Score merge candidates by confidence | Epic 8 | Story 8.4 | ✅ Covered |
| FR64 | Review and approve/reject merge suggestions | Epic 8 | Story 8.4 | ✅ Covered |

### NFR Coverage

| NFR | Requirement | Story | Status |
|-----|------------|-------|--------|
| NFR31 | OCR <60s per image page on min hardware | Story 7.2 | ✅ Covered |
| NFR32 | Web page capture <30s | Story 9.1 | ✅ Covered |
| NFR33 | Cross-investigation queries <15s | Stories 10.1, 10.2 | ✅ Covered |
| NFR34 | Atomic entity merge with rollback | Story 8.3 | ✅ Covered |

### PRD Phase 2 Feature List Traceability

| PRD Phase 2 Feature | FR Coverage | Status |
|---------------------|-------------|--------|
| Image OCR (Tesseract + moondream2) | FR48–FR51 | ✅ Covered |
| Manual entity creation, correction, and merge | FR52–FR55 | ✅ Covered |
| Web page ingestion (URL capture) | FR56–FR58 | ✅ Covered |
| Processed text preview per document | MVP FR10 + Story 7.3 enhancement | ✅ Covered (enhancement) |
| Cross-investigation entity linking and accumulation queries | FR59–FR61 | ✅ Covered |
| Improved entity disambiguation | FR62–FR64 | ✅ Covered |

### Missing Requirements

**Critical Missing FRs:** None

**High Priority Missing FRs:** None

### Coverage Statistics

- Total Phase 2 FRs: 17
- FRs covered in epics: 17
- Coverage percentage: **100%**
- Total Phase 2 NFRs: 4
- NFRs covered in stories: 4
- NFR coverage: **100%**
- PRD Phase 2 features: 6
- Features traced to FRs: 6
- Feature traceability: **100%**

## UX Alignment Assessment

### UX Document Status

**Found:** `ux-design-specification.md` (1,501 lines, created for MVP)

The UX spec was authored during MVP planning and defines the complete design system, component library, interaction patterns, and user flows for the MVP feature set. It does NOT contain Phase 2-specific component designs. However, it establishes the design language and patterns that Phase 2 features must follow.

### UX ↔ PRD Alignment (Phase 2)

**Aligned patterns (UX spec establishes reusable patterns for Phase 2):**

| Phase 2 Feature | UX Pattern Available | Source |
|-----------------|---------------------|--------|
| OCR quality indicators (FR51) | Confidence visual language: border thickness, badges, tooltips | UX §Confidence Indicators |
| Image document in processing dashboard (FR48) | Per-document status card pattern with SSE | UX §Processing Dashboard |
| Manual entity editing (FR53) | Entity Detail Card with properties and actions | UX §Entity Detail Card |
| Manual relationship creation (FR55) | Graph interaction patterns, edge click behavior | UX §Graph Canvas |
| Web page citations (FR58) | Citation Modal with filename, page, passage | UX §Citation Modal |
| OCR text viewer (FR51) | Extracted text preview via "View Text" action | UX §Extracted Text Viewer (Story 2.5) |

**PRD Journey 2 (Maria Edge Case) ↔ UX:**
- PRD Journey 2 explicitly describes the Phase 2 user needs (manual entity creation, merge, correction)
- UX spec references Journey 2 for "low confidence indicator" and "processed text view" patterns
- Alignment is consistent — both documents point to the same user problem and solution direction

### UX ↔ Architecture Alignment (Phase 2)

**Aligned:**
- Architecture's Entity Detail Card as non-focus-trapping dialog → extends naturally for edit/merge actions
- Architecture's SSE event system → extends to support image and web document processing events
- Architecture's single Qdrant collection with investigation_id filter → supports cross-investigation queries without schema change
- Architecture's RFC 7807 error handling → applies to new endpoints (entity CRUD, merge, web capture)
- Architecture's Cytoscape.js wrapper → extends for manual relationship creation interactions

### Alignment Issues

**⚠️ WARNING: No Phase 2-specific UX component designs**

The following Phase 2 UI components are referenced in stories but have no detailed UX specification:

| Component | Story | Gap Description |
|-----------|-------|-----------------|
| Entity merge preview (side-by-side comparison) | Story 8.3 | New UI pattern — merge preview showing both entities' relationships and sources. No UX spec exists. |
| "Review Duplicates" panel | Story 8.4 | New panel with merge candidate list, confidence scores, approve/reject actions. No UX spec. |
| "Add Entity" form | Story 8.1 | New form for manual entity creation. No UX spec — though simple enough to derive from shadcn/ui form patterns. |
| "Add Relationship" interaction | Story 8.2 | New graph interaction for drawing manual connections. No UX spec for the source/target/type selection flow. |
| "Capture Web Page" URL input | Story 9.1 | New input for URL submission. No UX spec — though straightforward. |
| "Cross-Investigation Links" panel | Story 10.1, 10.2 | Entirely new UI concept — entity matches across investigations with drill-down. No UX spec. |

### Impact Assessment

**Severity: MEDIUM (warning, not blocker)**

The MVP UX spec provides sufficient design language (color system, typography, spacing, component patterns, interaction principles) that Phase 2 features can be designed consistently by following established patterns. The story acceptance criteria describe the UI behavior in enough detail for implementation.

However, the more complex new UI concepts — particularly the **entity merge preview**, **duplicate review panel**, and **cross-investigation links panel** — would benefit from dedicated UX design to ensure they meet the same quality bar as MVP components.

### Recommendations

1. **Proceed with implementation** — the design language and component patterns are well-established enough for consistency
2. **Consider UX spec addendum** — before implementing Epic 8 (entity curation) and Epic 10 (cross-investigation), adding UX wireframes for the merge preview and cross-investigation panels would reduce implementation ambiguity
3. **Entity merge preview is the highest-risk UI** — it's a novel interaction (side-by-side entity comparison with relationship transfer visualization) that doesn't map to any existing UX pattern

## Epic Quality Review

### Epic Structure Validation

#### User Value Focus

| Epic | Title User-Centric? | Goal Describes User Outcome? | Standalone Value? | Verdict |
|------|---------------------|-----------------------------|--------------------|---------|
| Epic 7: Image Document Processing (OCR) | ✅ Yes | ✅ Upload images, get OCR extraction | ✅ Yes | PASS |
| Epic 8: Manual Entity Curation & Disambiguation | ✅ Yes | ✅ Fix errors, add entities, merge duplicates | ✅ Yes | PASS |
| Epic 9: Web Page Ingestion | ✅ Yes | ✅ Capture web pages as documents | ✅ Yes | PASS |
| Epic 10: Cross-Investigation Intelligence | ✅ Yes | ✅ Discover cross-case entity connections | ✅ Yes | PASS |

**No technical epics found.** All 4 epics deliver clear user value.

#### Epic Independence

| Test | Result |
|------|--------|
| Epic 7 standalone (no dependency on 8, 9, 10) | ✅ PASS — extends MVP pipeline independently |
| Epic 8 standalone (no dependency on 7, 9, 10) | ✅ PASS — works with MVP-extracted entities |
| Epic 9 standalone (no dependency on 7, 8, 10) | ✅ PASS — extends MVP pipeline independently |
| Epic 10 standalone (no dependency on 7, 8, 9) | ✅ PASS — queries existing MVP data |
| No epic requires a future epic to function | ✅ PASS |
| No circular dependencies | ✅ PASS |

### Story Dependency Analysis (Within-Epic)

**Epic 7:**
- Story 7.1 → completable alone ✅
- Story 7.2 → depends on 7.1 (image pipeline) — backward ✅
- Story 7.3 → depends on 7.1/7.2 (OCR output) — backward ✅
- No forward dependencies ✅

**Epic 8:**
- Story 8.1 → completable alone ✅
- Story 8.2 → depends on 8.1 (entities exist to connect) — backward ✅
- Story 8.3 → depends on 8.1 (entities exist to merge) — backward ✅
- Story 8.4 → depends on 8.3 (merge flow for approve action) — backward ✅
- No forward dependencies ✅

**Epic 9:**
- Story 9.1 → completable alone ✅
- Story 9.2 → depends on 9.1 (captured page exists) — backward ✅
- No forward dependencies ✅

**Epic 10:**
- Story 10.1 → completable alone ✅
- Story 10.2 → depends on 10.1 (matches exist) — backward ✅
- No forward dependencies ✅

### Database/Entity Creation Timing

| Story | Schema Change | When Needed? | Verdict |
|-------|--------------|-------------|---------|
| 7.1 | Adds `document_type` field to document records | When image upload is implemented | ✅ PASS |
| 8.1 | Adds `source="manual"`, `aliases` Neo4j properties | When manual entity creation is implemented | ✅ PASS |
| 8.4 | Adds Neo4j full-text indexes for fuzzy matching | When disambiguation is implemented | ✅ PASS |
| 9.1 | Adds `document_type="web"` to document records | When web capture is implemented | ✅ PASS |

No upfront schema setup. Tables/properties created only when first needed. ✅

### Story Acceptance Criteria Quality

| Criteria | All 11 Stories? | Notes |
|----------|----------------|-------|
| Given/When/Then format | ✅ Yes | All stories use proper BDD structure |
| Independently testable ACs | ✅ Yes | Each AC can be verified in isolation |
| Error conditions covered | ✅ Yes | All stories include failure/edge cases |
| Specific expected outcomes | ✅ Yes | No vague "user can do X" without measurable result |
| NFR targets in ACs where applicable | ✅ Yes | NFR31 in 7.2, NFR32 in 9.1, NFR33 in 10.1/10.2, NFR34 in 8.3 |

### Best Practices Compliance Checklist

| Check | Epic 7 | Epic 8 | Epic 9 | Epic 10 |
|-------|--------|--------|--------|---------|
| Epic delivers user value | ✅ | ✅ | ✅ | ✅ |
| Epic can function independently | ✅ | ✅ | ✅ | ✅ |
| Stories appropriately sized | ✅ | ✅ | ✅ | ✅ |
| No forward dependencies | ✅ | ✅ | ✅ | ✅ |
| Database changes when needed | ✅ | ✅ | ✅ | ✅ |
| Clear acceptance criteria | ✅ | ✅ | ✅ | ✅ |
| Traceability to FRs maintained | ✅ | ✅ | ✅ | ✅ |

### Quality Findings

#### 🔴 Critical Violations

**None found.**

#### 🟠 Major Issues

**None found.**

#### 🟡 Minor Concerns

**1. Story 7.2 — "configurable threshold" for moondream2 routing is underspecified**
- AC says: "the OCR output quality is below a configurable threshold"
- Does not specify who configures it, where, or default values
- **Remediation:** Story AC should specify a sensible default threshold with the configuration mechanism (e.g., environment variable, config file). Low risk — dev agent can make a reasonable choice during implementation.

**2. Story 8.4 — automatic duplicate detection after document processing may impact pipeline performance**
- AC says: "the system runs duplicate detection against existing entities for the newly extracted ones"
- This adds a background process to the existing document processing pipeline. Performance impact on the MVP pipeline is not quantified.
- **Remediation:** Consider adding a note that duplicate detection runs asynchronously after processing completion, not blocking the processing pipeline. Low risk.

**3. Story 9.1 — no security considerations for fetching arbitrary URLs**
- AC covers URL validation and timeout but does not address: SSRF prevention, maximum page size limits, handling of JavaScript-rendered pages, or redirect limits.
- **Remediation:** For a local-first single-user tool, SSRF risk is low. But AC could include maximum page size and redirect depth limits. Low risk for MVP scope.

**4. Story 10.2 — cross-investigation navigation is a new router pattern**
- AC says clicking "Open in Investigation" navigates to another investigation's workspace. This is the first cross-investigation navigation in the app. TanStack Router should handle this naturally, but it's a new interaction pattern.
- **Remediation:** None needed — standard router navigation. Noting for awareness.

### Quality Assessment Summary

**Overall quality: HIGH**

- 0 critical violations
- 0 major issues
- 4 minor concerns (all low-risk, addressable during implementation)
- All best practices complied with
- Clean dependency structure with no forward references
- Database changes correctly scoped to individual stories

## Summary and Recommendations

### Overall Readiness Status

### **READY** — with minor recommendations

Phase 2 (v1.1) is ready for sprint planning and implementation. All requirements are fully traced, epics are structurally sound, and no critical or major issues were found.

### Assessment Summary

| Category | Finding |
|----------|---------|
| **FR Coverage** | 17/17 FRs covered (100%) |
| **NFR Coverage** | 4/4 NFRs covered (100%) |
| **PRD Feature Traceability** | 6/6 Phase 2 features traced (100%) |
| **Epic Structure** | 4 epics, all deliver user value, all independent |
| **Story Quality** | 11 stories, all with Given/When/Then ACs, no forward dependencies |
| **UX Alignment** | Aligned on reusable patterns; 6 new components lack dedicated UX designs |
| **Critical Violations** | 0 |
| **Major Issues** | 0 |
| **Minor Concerns** | 4 |

### Critical Issues Requiring Immediate Action

**None.** No blockers to proceeding with implementation.

### Recommended Actions Before Sprint Planning

1. **Consider a UX spec addendum for Epic 8 and Epic 10** — The entity merge preview (Story 8.3), duplicate review panel (Story 8.4), and cross-investigation links panel (Stories 10.1/10.2) are novel UI concepts with no existing UX specification. Adding wireframes would reduce implementation ambiguity. Priority: Medium. Can be done during sprint planning or in parallel with Epic 7 implementation.

2. **Refine Story 7.2 threshold configuration** — The "configurable threshold" for moondream2 routing should specify a default value and configuration mechanism. This can be addressed when the story is prepared for implementation. Priority: Low.

3. **Add URL security bounds to Story 9.1** — Consider adding maximum page size limit and redirect depth limit to the acceptance criteria. Low risk for a local-first tool but good practice. Priority: Low.

### Recommended Implementation Order

1. **Epic 7** (Image OCR) — extends existing pipeline, lowest risk, no new UI patterns
2. **Epic 8** (Entity Curation) — highest UX complexity, benefits from UX spec addendum
3. **Epic 9** (Web Ingestion) — introduces privacy model change, independent of other epics
4. **Epic 10** (Cross-Investigation) — most novel feature, benefits from entity disambiguation (Epic 8) being live first

### Final Note

This assessment identified 4 minor concerns and 1 medium-severity UX gap across 5 validation categories. All findings are actionable during sprint planning or implementation — none require rework of the epics document. The Phase 2 planning artifacts are comprehensive and well-aligned with the existing PRD, Architecture, and UX specifications.

**Assessed by:** Implementation Readiness Workflow
**Date:** 2026-04-12
**Artifacts reviewed:** prd.md, architecture.md, epics-phase2.md, ux-design-specification.md
