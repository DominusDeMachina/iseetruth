"""GRAPH FIRST query pipeline service.

Translates natural language questions into Cypher + vector searches,
executes against Neo4j/Qdrant, merges results with provenance, and
formats cited prose via LLM.
"""

import asyncio
import json
import re
import uuid
from typing import Any, AsyncGenerator

from loguru import logger
from qdrant_client.models import FieldCondition, Filter, MatchValue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.qdrant import COLLECTION_NAME
from app.exceptions import GraphUnavailableError, OllamaUnavailableError
from app.llm.client import DEFAULT_MODEL, OllamaClient
from app.llm.embeddings import OllamaEmbeddingClient
from app.llm.prompts import (
    ANSWER_FORMATTING_SYSTEM_PROMPT,
    ANSWER_FORMATTING_USER_PROMPT_TEMPLATE,
    QUERY_TRANSLATION_SYSTEM_PROMPT,
    QUERY_TRANSLATION_USER_PROMPT_TEMPLATE,
    SUGGESTED_FOLLOWUPS_PROMPT,
)
from app.llm.schemas import QueryTranslation
from app.models.document import Document
from app.schemas.query import Citation, EntityReference, QueryResponse
from app.services.events import EventPublisher


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def execute_query(
    investigation_id: str,
    question: str,
    conversation_history: list[dict] | None,
    neo4j_driver,
    qdrant_client,
    ollama_client: OllamaClient,
    embedding_client: OllamaEmbeddingClient,
    event_publisher: EventPublisher,
    db: AsyncSession,
    query_id: str | None = None,
) -> AsyncGenerator[dict, None]:
    """Execute the GRAPH FIRST query pipeline, yielding SSE events.

    Yields dicts with ``event`` and ``data`` keys suitable for SSE streaming.
    """
    query_id = query_id or str(uuid.uuid4())

    try:
        # Phase 1 — Translate
        yield _sse("query.translating", {"query_id": query_id, "message": "Translating your question..."})
        event_publisher.publish(investigation_id, "query.translating", {"query_id": query_id})

        translation = await asyncio.to_thread(
            _translate_question, ollama_client, investigation_id, question, conversation_history
        )
        logger.info(
            "Query translation result | cypher={} | terms={} | entities={}",
            translation.cypher_queries, translation.search_terms, translation.entity_names,
        )

        # Phase 2 — Search (graph + vector in parallel)
        yield _sse("query.searching", {"query_id": query_id, "message": "Searching knowledge graph and documents..."})
        event_publisher.publish(investigation_id, "query.searching", {"query_id": query_id})

        graph_task = _search_graph(neo4j_driver, investigation_id, translation)
        vector_task = _search_vectors(qdrant_client, embedding_client, investigation_id, question)

        graph_results, vector_results = await asyncio.gather(
            graph_task, vector_task, return_exceptions=True
        )

        # Handle Qdrant degradation — continue with graph-only if vector search fails
        if isinstance(vector_results, Exception):
            logger.warning("Vector search failed, continuing with graph-only results", error=str(vector_results))
            vector_results = []
        if isinstance(graph_results, Exception):
            raise GraphUnavailableError(f"Graph search failed: {graph_results}")

        logger.info(
            "Search results | graph={} | vector={} | vector_scores={}",
            len(graph_results),
            len(vector_results),
            [round(r.get("score", 0), 3) for r in vector_results] if isinstance(vector_results, list) else [],
        )
        if graph_results:
            logger.info("Graph result records: {}", graph_results[:5])

        # Phase 3 — Merge results
        citations, entities_mentioned, graph_text, vector_text = await _merge_results(
            graph_results, vector_results, db
        )

        logger.info(
            "Merge results | citations={} | entities={}",
            len(citations), len(entities_mentioned),
        )

        # Phase 4 — Check for empty results
        if not citations:
            no_result_response = QueryResponse(
                query_id=query_id,
                answer="No connection found in your documents.",
                citations=[],
                entities_mentioned=[],
                no_results=True,
            )
            yield _sse("query.complete", no_result_response.model_dump())
            event_publisher.publish(investigation_id, "query.complete", {"query_id": query_id, "no_results": True})
            return

        # Phase 5 — Format answer
        citation_text = _format_citation_list(citations)

        answer_text = await asyncio.to_thread(
            _format_answer, ollama_client, question, graph_text, vector_text, citation_text
        )
        full_answer = answer_text
        yield _sse("query.streaming", {"query_id": query_id, "chunk": full_answer})

        # Phase 6 — Follow-up suggestions
        suggested_followups = await asyncio.to_thread(
            _generate_followups, ollama_client, question, full_answer, entities_mentioned
        )

        # Phase 7 — Complete
        response = QueryResponse(
            query_id=query_id,
            answer=full_answer,
            citations=citations,
            entities_mentioned=entities_mentioned,
            suggested_followups=suggested_followups,
        )
        yield _sse("query.complete", response.model_dump())
        event_publisher.publish(investigation_id, "query.complete", {
            "query_id": query_id,
            "answer": full_answer,
            "citations": [c.model_dump() for c in citations],
            "entities_mentioned": [e.model_dump() for e in entities_mentioned],
            "suggested_followups": suggested_followups,
        })

    except GraphUnavailableError as exc:
        logger.error("Graph unavailable during query pipeline", error=str(exc))
        yield _sse("query.failed", {"query_id": query_id, "error": "Knowledge graph service unavailable"})
        event_publisher.publish(investigation_id, "query.failed", {"query_id": query_id, "error": str(exc)})
        raise
    except OllamaUnavailableError as exc:
        logger.error("LLM unavailable during query pipeline", error=str(exc))
        yield _sse("query.failed", {"query_id": query_id, "error": "LLM service unavailable"})
        event_publisher.publish(investigation_id, "query.failed", {"query_id": query_id, "error": str(exc)})
        raise
    except Exception as exc:
        logger.error("Query pipeline failed", error=str(exc))
        yield _sse("query.failed", {"query_id": query_id, "error": str(exc)})
        event_publisher.publish(investigation_id, "query.failed", {"query_id": query_id, "error": str(exc)})
        raise


# ---------------------------------------------------------------------------
# Phase 1 — Query Translation
# ---------------------------------------------------------------------------


def _translate_question(
    ollama_client: OllamaClient,
    investigation_id: str,
    question: str,
    conversation_history: list[dict] | None,
) -> QueryTranslation:
    """Translate natural language question to Cypher + vector search terms."""
    messages = [{"role": "system", "content": QUERY_TRANSLATION_SYSTEM_PROMPT}]

    if conversation_history:
        for turn in conversation_history:
            messages.append({"role": turn["role"], "content": turn["content"]})

    user_content = QUERY_TRANSLATION_USER_PROMPT_TEMPLATE.format(
        investigation_id=investigation_id,
        question=question,
    )
    messages.append({"role": "user", "content": user_content})

    response = ollama_client.chat(model=DEFAULT_MODEL, messages=messages, format="json")
    content = response.get("message", {}).get("content", "")

    try:
        parsed = json.loads(content)
        return QueryTranslation(**parsed)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("LLM returned invalid translation JSON, falling back", error=str(exc))
        return _fallback_translation(question)


def _fallback_translation(question: str) -> QueryTranslation:
    """Extract entity names from question using simple heuristics."""
    # Extract capitalized words/phrases and quoted strings
    quoted = re.findall(r'"([^"]+)"', question)
    # Capitalized Latin words that aren't common English words
    stop_words = {
        "The", "What", "Who", "Where", "When", "How", "Why", "Which",
        "Does", "Did", "Are", "Is", "Was", "Were", "Has", "Have", "Had",
        "Can", "Could", "Would", "Should", "Do", "Will", "May", "Might",
        "Any", "All", "Some", "Between", "About", "From", "With", "And",
        "For", "Not", "But", "This", "That", "There", "Their", "They",
    }
    capitalized = [
        w for w in re.findall(r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\b", question)
        if w not in stop_words
    ]
    # Cyrillic capitalized words (Ukrainian/Russian entity names)
    cyrillic_stop = {
        "Як", "Що", "Хто", "Де", "Коли", "Чому", "Який", "Яка", "Яке",
        "Чи", "Або", "Але", "Цей", "Ця", "Це", "Той", "Та", "Те",
        "Між", "Про", "Від", "Для", "Так", "Ні", "Він", "Вона", "Вони",
        "Як", "Что", "Кто", "Где", "Когда", "Почему", "Какой", "Какая",
        "Или", "Но", "Этот", "Эта", "Это", "Тот", "Между", "Про",
    }
    cyrillic = [
        w for w in re.findall(r"\b([А-ЯІЇЄҐЁA-Z][а-яіїєґёa-z]+(?:\s+[А-ЯІЇЄҐЁA-Z][а-яіїєґёa-z]+)*)\b", question)
        if w not in cyrillic_stop
    ]
    entity_names = list(dict.fromkeys(quoted + capitalized + cyrillic))  # deduplicate, preserve order

    # Build fallback Cypher: find entities by name and shortest paths between them
    # Uses $entity_name_N parameters — values are provided by _search_graph
    cypher_queries = []
    if len(entity_names) >= 2:
        cypher_queries.append(
            "MATCH p = shortestPath((a)-[*..5]-(b)) "
            "WHERE a.investigation_id = $investigation_id "
            "AND b.investigation_id = $investigation_id "
            "AND toLower(a.name) CONTAINS toLower($entity_name_0) "
            "AND toLower(b.name) CONTAINS toLower($entity_name_1) "
            "RETURN p"
        )
    elif len(entity_names) == 1:
        cypher_queries.append(
            "MATCH (e:Person|Organization|Location {investigation_id: $investigation_id}) "
            "WHERE toLower(e.name) CONTAINS toLower($entity_name_0) "
            "OPTIONAL MATCH (e)-[r:WORKS_FOR|KNOWS|LOCATED_AT]-(t {investigation_id: $investigation_id}) "
            "RETURN e, r, t LIMIT 20"
        )

    return QueryTranslation(
        cypher_queries=cypher_queries,
        search_terms=[question],
        entity_names=entity_names,
    )


# ---------------------------------------------------------------------------
# Phase 2 — Graph Search
# ---------------------------------------------------------------------------


def _validate_cypher(cypher: str) -> str | None:
    """Return an error message if the Cypher has obvious syntax issues, else None."""
    upper = cypher.upper()
    # Block write operations
    for keyword in ("CREATE", "DELETE", "SET ", "MERGE", "REMOVE"):
        if keyword in upper:
            return f"Write operation '{keyword.strip()}' not allowed"
    # Check for undefined variables in RETURN — every returned name must appear
    # in a MATCH/WITH/UNWIND clause binding (variable before a colon or as alias)
    return None


async def _search_graph(
    neo4j_driver,
    investigation_id: str,
    translation: QueryTranslation,
) -> list[dict]:
    """Execute Cypher queries and resolve provenance."""
    all_results: list[dict] = []

    # Build parameterized query params (entity names for fallback Cypher)
    params = {"investigation_id": investigation_id}
    for i, name in enumerate(translation.entity_names):
        params[f"entity_name_{i}"] = name

    async with neo4j_driver.session() as session:
        for cypher in translation.cypher_queries:
            validation_error = _validate_cypher(cypher)
            if validation_error:
                logger.warning(f"Cypher validation failed, skipping: {validation_error}\n  Cypher: {cypher}")
                continue
            try:
                records = await session.execute_read(
                    _run_cypher, cypher, params
                )
                all_results.extend(records)
            except Exception as exc:
                logger.warning(f"Cypher query failed, skipping: {exc}\n  Cypher: {cypher}")

        # If Cypher produced no results, try entity name lookup as fallback
        if not all_results and translation.entity_names:
            records = await session.execute_read(
                _fetch_entities_by_names, investigation_id, translation.entity_names
            )
            all_results.extend(records)

        # Resolve provenance for all discovered entities
        entity_ids = _extract_entity_ids(all_results)
        if entity_ids:
            provenance = await session.execute_read(
                _resolve_provenance, entity_ids
            )
            # Attach provenance to results
            for result in all_results:
                eid = result.get("entity_id") or result.get("id")
                if eid and eid in provenance:
                    result["provenance"] = provenance[eid]

    return all_results


async def _run_cypher(tx, cypher: str, params: dict) -> list[dict]:
    """Execute a single Cypher query within a read transaction."""
    result = await tx.run(cypher, **params)
    records = await result.data()

    # Normalize path results into entity/relationship records
    normalized = []
    for record in records:
        for key, value in record.items():
            if hasattr(value, "nodes") and hasattr(value, "relationships"):
                # Native Path object (sync driver)
                for node in value.nodes:
                    props = dict(node.items())
                    labels = list(node.labels)
                    normalized.append({
                        "entity_id": props.get("id"),
                        "id": props.get("id"),
                        "name": props.get("name"),
                        "type": labels[0] if labels else "Unknown",
                        "confidence_score": props.get("confidence_score", 0.0),
                    })
                for rel in value.relationships:
                    props = dict(rel.items())
                    normalized.append({
                        "relationship_type": rel.type,
                        "source_id": dict(rel.start_node.items()).get("id") if rel.start_node else None,
                        "target_id": dict(rel.end_node.items()).get("id") if rel.end_node else None,
                        **props,
                    })
            elif isinstance(value, list) and _is_serialized_path(value):
                # Serialized path from .data() — alternating node dicts and relationship strings
                _normalize_serialized_path(value, normalized)
            elif isinstance(value, dict) or hasattr(value, "items"):
                # Node result
                props = dict(value.items()) if hasattr(value, "items") else value
                normalized.append(props)
            else:
                # Scalar or other value — include in a flat record
                normalized.append(record)
                break

    return normalized if normalized else records


def _is_serialized_path(value: list) -> bool:
    """Check if a list is a serialized Neo4j path (alternating node dicts and relationship strings)."""
    if len(value) < 3 or len(value) % 2 == 0:
        return False
    # Odd positions should be dicts (nodes), even positions should be strings (rel types)
    return (
        isinstance(value[0], dict)
        and isinstance(value[1], str)
        and isinstance(value[2], dict)
    )


def _normalize_serialized_path(path: list, normalized: list[dict]) -> None:
    """Extract entity and relationship records from a serialized path list."""
    nodes = []
    for i, item in enumerate(path):
        if i % 2 == 0 and isinstance(item, dict):
            # Node dict
            node_type = item.get("type", "Unknown")
            # Capitalize type to match label convention (person -> Person)
            if isinstance(node_type, str):
                node_type = node_type.capitalize()
            normalized.append({
                "entity_id": item.get("id"),
                "id": item.get("id"),
                "name": item.get("name"),
                "type": node_type,
                "confidence_score": item.get("confidence_score", 0.0),
            })
            nodes.append(item)
        elif i % 2 == 1 and isinstance(item, str):
            # Relationship type string — pair with surrounding nodes
            source = nodes[-1] if nodes else None
            target = path[i + 1] if i + 1 < len(path) and isinstance(path[i + 1], dict) else None
            normalized.append({
                "relationship_type": item,
                "source_id": source.get("id") if source else None,
                "target_id": target.get("id") if target else None,
                "source_name": source.get("name") if source else None,
                "target_name": target.get("name") if target else None,
            })


async def _fetch_entities_by_names(tx, investigation_id: str, entity_names: list[str]) -> list[dict]:
    """Fallback: find entities by name matching."""
    params: dict[str, str] = {"investigation_id": investigation_id}
    conditions = []
    for i, name in enumerate(entity_names):
        param_key = f"name_{i}"
        conditions.append(f"toLower(e.name) CONTAINS toLower(${param_key})")
        params[param_key] = name
    where_clause = " OR ".join(conditions)
    query = (
        f"MATCH (e:Person|Organization|Location {{investigation_id: $investigation_id}}) "
        f"WHERE {where_clause} "
        "OPTIONAL MATCH (e)-[r:WORKS_FOR|KNOWS|LOCATED_AT]-(t {investigation_id: $investigation_id}) "
        "RETURN e.id AS entity_id, e.id AS id, e.name AS name, labels(e)[0] AS type, "
        "e.confidence_score AS confidence_score, "
        "type(r) AS relationship_type, t.id AS target_id, t.name AS target_name, "
        "labels(t)[0] AS target_type"
    )
    result = await tx.run(query, **params)
    return await result.data()


# ---------------------------------------------------------------------------
# Phase 2b — Provenance Resolution (Task 5)
# ---------------------------------------------------------------------------


async def _resolve_provenance(tx, entity_ids: list[str]) -> dict[str, list[dict]]:
    """Resolve MENTIONED_IN provenance for entities."""
    result = await tx.run(
        "MATCH (e)-[m:MENTIONED_IN]->(d:Document) "
        "WHERE e.id IN $entity_ids "
        "RETURN e.id AS entity_id, m.chunk_id AS chunk_id, "
        "m.page_start AS page_start, m.page_end AS page_end, "
        "m.text_excerpt AS text_excerpt, d.id AS document_id",
        entity_ids=entity_ids,
    )
    records = await result.data()

    provenance: dict[str, list[dict]] = {}
    for r in records:
        eid = r["entity_id"]
        if eid not in provenance:
            provenance[eid] = []
        provenance[eid].append({
            "chunk_id": r["chunk_id"],
            "page_start": r["page_start"],
            "page_end": r["page_end"],
            "text_excerpt": r["text_excerpt"],
            "document_id": r["document_id"],
        })

    return provenance


async def _resolve_document_filenames(document_ids: list[str], db: AsyncSession) -> dict[str, str]:
    """Query PostgreSQL documents table for filenames by ID."""
    if not document_ids:
        return {}
    try:
        result = await db.execute(
            select(Document.id, Document.filename).where(
                Document.id.in_([uuid.UUID(d) for d in document_ids])
            )
        )
        return {str(row.id): row.filename for row in result}
    except Exception as exc:
        logger.warning("Failed to resolve document filenames", error=str(exc))
        return {}


# ---------------------------------------------------------------------------
# Phase 2c — Vector Search
# ---------------------------------------------------------------------------


async def _search_vectors(
    qdrant_client,
    embedding_client: OllamaEmbeddingClient,
    investigation_id: str,
    question: str,
) -> list[dict]:
    """Embed question and search Qdrant for relevant chunks."""
    # Embed the question
    vector = await asyncio.to_thread(embedding_client.embed, question)

    # Search Qdrant with investigation_id filter
    search_result = await asyncio.to_thread(
        qdrant_client.query_points,
        collection_name=COLLECTION_NAME,
        query=vector,
        query_filter=Filter(
            must=[FieldCondition(key="investigation_id", match=MatchValue(value=investigation_id))]
        ),
        limit=10,
    )

    results = []
    for point in search_result.points:
        payload = point.payload or {}
        results.append({
            "chunk_id": payload.get("chunk_id"),
            "document_id": payload.get("document_id"),
            "page_start": payload.get("page_start"),
            "page_end": payload.get("page_end"),
            "text_excerpt": payload.get("text_excerpt", ""),
            "score": point.score,
        })

    return results


# ---------------------------------------------------------------------------
# Phase 3 — Result Merge
# ---------------------------------------------------------------------------


_VECTOR_RELEVANCE_THRESHOLD = 0.2


_MAX_CITATIONS = 15


async def _merge_results(
    graph_results: list[dict],
    vector_results: list[dict],
    db: AsyncSession,
) -> tuple[list[Citation], list[EntityReference], str, str]:
    """Merge graph and vector results, deduplicate by document+page, build citations."""
    seen_pages: set[str] = set()
    seen_chunks: set[str] = set()
    citation_sources: list[dict] = []
    entities_seen: dict[str, EntityReference] = {}

    # Collect entities and provenance from graph results
    for record in graph_results:
        eid = record.get("entity_id") or record.get("id")
        name = record.get("name")
        etype = record.get("type")
        if eid and name and etype:
            if eid not in entities_seen:
                entities_seen[eid] = EntityReference(entity_id=eid, name=name, type=etype)

        # Add provenance chunks — deduplicate by (document_id, page_start) so the
        # same page doesn't appear multiple times in the citation footer.
        for prov in record.get("provenance", []):
            page_key = f"{prov['document_id']}:{prov.get('page_start', 0)}"
            chunk_key = f"{prov['document_id']}:{prov['chunk_id']}"
            if page_key not in seen_pages:
                seen_pages.add(page_key)
                seen_chunks.add(chunk_key)
                citation_sources.append(prov)

    # Filter vector results by relevance score to avoid irrelevant noise
    relevant_vectors = [
        vr for vr in vector_results
        if vr.get("score", 0) >= _VECTOR_RELEVANCE_THRESHOLD
    ]

    # Add vector results (deduplicate by document+page, fall back to chunk)
    for vr in relevant_vectors:
        page_key = f"{vr['document_id']}:{vr.get('page_start', 0)}"
        chunk_key = f"{vr['document_id']}:{vr['chunk_id']}"
        if page_key not in seen_pages and chunk_key not in seen_chunks:
            seen_pages.add(page_key)
            seen_chunks.add(chunk_key)
            citation_sources.append(vr)

    # Cap total citations to keep the footer manageable
    citation_sources = citation_sources[:_MAX_CITATIONS]

    # Resolve document filenames
    doc_ids = list({cs["document_id"] for cs in citation_sources if cs.get("document_id")})
    filename_map = await _resolve_document_filenames(doc_ids, db)

    # Build numbered citations
    citations: list[Citation] = []
    for i, source in enumerate(citation_sources, start=1):
        citations.append(Citation(
            citation_number=i,
            document_id=source.get("document_id", ""),
            document_filename=filename_map.get(source.get("document_id", ""), "unknown"),
            chunk_id=source.get("chunk_id", ""),
            page_start=source.get("page_start", 0) or 0,
            page_end=source.get("page_end", 0) or 0,
            text_excerpt=source.get("text_excerpt", ""),
        ))

    entities_mentioned = list(entities_seen.values())

    # Format text representations for LLM (use filtered vectors only)
    graph_text = _format_graph_results(graph_results)
    vector_text = _format_vector_results(relevant_vectors)

    return citations, entities_mentioned, graph_text, vector_text


def _format_graph_results(results: list[dict]) -> str:
    """Format graph results as text for the LLM."""
    if not results:
        return "No graph results found."

    lines = []
    entities = {}
    relationships = []

    # First pass: collect all entity ID -> name mappings
    for r in results:
        eid = r.get("entity_id") or r.get("id")
        if eid and r.get("name"):
            entities[eid] = f"{r['name']} ({r.get('type', 'Unknown')})"

    # Second pass: build relationships using entity names
    for r in results:
        if r.get("relationship_type"):
            source = r.get("source_id") or r.get("entity_id") or r.get("id")
            target = r.get("target_id")
            # Resolve names: prefer explicit target_name, then lookup in entities dict, then raw ID
            source_label = entities.get(source, r.get("name", source))
            target_label = r.get("target_name") or entities.get(target, target)
            if source and target:
                relationships.append(f"{source_label} --[{r['relationship_type']}]--> {target_label}")

        # Include provenance excerpts
        for prov in r.get("provenance", []):
            lines.append(f"Source (doc:{prov['document_id']}, chunk:{prov['chunk_id']}, pages {prov['page_start']}-{prov['page_end']}): {prov['text_excerpt']}")

    entity_lines = [f"Entity: {v}" for v in entities.values()]
    rel_lines = [f"Relationship: {r}" for r in relationships]

    return "\n".join(entity_lines + rel_lines + lines)


def _format_vector_results(results: list[dict]) -> str:
    """Format vector search results as text for the LLM."""
    if not results:
        return "No vector search results found."

    lines = []
    for r in results:
        lines.append(
            f"Chunk (doc:{r.get('document_id')}, pages {r.get('page_start', '?')}-{r.get('page_end', '?')}, "
            f"relevance:{r.get('score', 0):.2f}): {r.get('text_excerpt', '')}"
        )
    return "\n".join(lines)


def _format_citation_list(citations: list[Citation]) -> str:
    """Format citation list for the LLM."""
    lines = []
    for c in citations:
        lines.append(
            f"[{c.citation_number}] {c.document_filename} (pages {c.page_start}-{c.page_end}): "
            f"{c.text_excerpt[:200]}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Phase 5 — Answer Formatting
# ---------------------------------------------------------------------------


def _format_answer(
    ollama_client: OllamaClient,
    question: str,
    graph_text: str,
    vector_text: str,
    citation_text: str,
) -> str:
    """Call LLM to format results as cited prose."""
    messages = [
        {"role": "system", "content": ANSWER_FORMATTING_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": ANSWER_FORMATTING_USER_PROMPT_TEMPLATE.format(
                question=question,
                graph_results=graph_text,
                vector_results=vector_text,
                citation_list=citation_text,
            ),
        },
    ]
    response = ollama_client.chat(model=DEFAULT_MODEL, messages=messages)
    return response.get("message", {}).get("content", "")


# ---------------------------------------------------------------------------
# Phase 6 — Follow-up Suggestions
# ---------------------------------------------------------------------------


def _generate_followups(
    ollama_client: OllamaClient,
    question: str,
    answer: str,
    entities: list[EntityReference],
) -> list[str]:
    """Generate follow-up question suggestions."""
    entity_names = ", ".join(e.name for e in entities) if entities else "none"
    prompt = SUGGESTED_FOLLOWUPS_PROMPT.format(
        question=question,
        answer=answer,
        entities=entity_names,
    )
    try:
        response = ollama_client.generate(model=DEFAULT_MODEL, prompt=prompt, format="json")
        parsed = json.loads(response)
        logger.info("Follow-ups parsed response", parsed=parsed)
        if isinstance(parsed, list):
            return [str(q) for q in parsed[:3]]
        if isinstance(parsed, dict) and "followups" in parsed:
            return [str(q) for q in parsed["followups"][:3]]
        return []
    except (json.JSONDecodeError, OllamaUnavailableError) as exc:
        logger.warning("Failed to generate follow-ups", error=str(exc))
        return []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sse(event: str, data: Any) -> dict:
    """Build an SSE event dict."""
    return {"event": event, "data": data}


def _extract_entity_ids(results: list[dict]) -> list[str]:
    """Extract unique entity IDs from graph results."""
    ids = set()
    for r in results:
        eid = r.get("entity_id") or r.get("id")
        if eid:
            ids.add(eid)
        tid = r.get("target_id")
        if tid:
            ids.add(tid)
    return list(ids)
