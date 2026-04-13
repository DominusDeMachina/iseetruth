import uuid

from loguru import logger
from neo4j.exceptions import ConstraintError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import EntityDuplicateError, EntityMergeError
from app.models.document import Document
from app.schemas.entity import (
    EntityDetailResponse,
    EntityListItem,
    EntityListResponse,
    EntityMergePreview,
    EntityMergeResponse,
    EntityRelationship,
    EntitySource,
    EntityTypeSummary,
)


class EntityQueryService:
    def __init__(self, neo4j_driver, db: AsyncSession):
        self.neo4j_driver = neo4j_driver
        self.db = db

    async def list_entities(
        self,
        investigation_id: uuid.UUID,
        entity_type: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> EntityListResponse:
        """Return paginated entity list with confidence scores and summary counts."""
        inv_id_str = str(investigation_id)
        # Treat empty string search as no search
        effective_search = search if search and search.strip() else None

        async with self.neo4j_driver.session() as session:
            # Fetch all entities (pre-pagination) for summary counts
            all_records = await session.execute_read(
                _fetch_entity_list, inv_id_str, entity_type, effective_search
            )

        # Compute summary from full result set
        type_counts: dict[str, int] = {"Person": 0, "Organization": 0, "Location": 0}
        for record in all_records:
            label = record["type"]
            if label in type_counts:
                type_counts[label] += 1

        summary = EntityTypeSummary(
            people=type_counts["Person"],
            organizations=type_counts["Organization"],
            locations=type_counts["Location"],
            total=len(all_records),
        )

        # Sort by confidence DESC, apply pagination
        sorted_records = sorted(
            all_records, key=lambda r: r.get("confidence_score") or 0.0, reverse=True
        )
        paginated = sorted_records[offset : offset + limit]

        items = [
            EntityListItem(
                id=r["id"],
                name=r["name"],
                type=r["type"].lower(),
                confidence_score=r.get("confidence_score") or 0.0,
                source_count=r.get("source_count") or 0,
                evidence_strength=(
                    "corroborated"
                    if (r.get("source_count") or 0) >= 2
                    else "single_source"
                    if (r.get("source_count") or 0) == 1
                    else "none"
                ),
                source=r.get("source") or "extracted",
            )
            for r in paginated
        ]

        return EntityListResponse(
            items=items,
            total=summary.total,
            summary=summary,
        )

    async def create_entity(
        self,
        investigation_id: uuid.UUID,
        name: str,
        entity_type: str,
        source_annotation: str | None = None,
    ) -> EntityDetailResponse:
        """Create a manual entity in Neo4j and return its detail."""
        inv_id_str = str(investigation_id)
        entity_id = str(uuid.uuid4())
        label = entity_type.capitalize()

        async with self.neo4j_driver.session() as session:
            try:
                record = await session.execute_write(
                    _create_entity,
                    entity_id,
                    name,
                    entity_type,
                    inv_id_str,
                    source_annotation,
                    label,
                )
            except ConstraintError:
                raise EntityDuplicateError(name, entity_type)

        logger.info(
            "Manual entity created",
            entity_id=entity_id,
            name=name,
            type=entity_type,
            investigation_id=inv_id_str,
        )

        return EntityDetailResponse(
            id=entity_id,
            name=name,
            type=entity_type,
            confidence_score=1.0,
            investigation_id=inv_id_str,
            relationships=[],
            sources=[],
            evidence_strength="none",
            source="manual",
            source_annotation=source_annotation,
            aliases=[],
        )

    async def update_entity(
        self,
        investigation_id: uuid.UUID,
        entity_id: str,
        name: str | None = None,
        source_annotation: str | None = None,
    ) -> EntityDetailResponse | None:
        """Update an existing entity's name and/or source_annotation.

        Returns None if entity not found. Appends old name to aliases when
        the name changes.
        """
        inv_id_str = str(investigation_id)

        # Fetch existing entity first to get current values
        async with self.neo4j_driver.session() as session:
            existing = await session.execute_read(
                _fetch_entity, entity_id, inv_id_str
            )
            if existing is None:
                return None

            old_name = existing["name"]
            name_changed = name is not None and name != old_name

            try:
                await session.execute_write(
                    _update_entity,
                    entity_id,
                    inv_id_str,
                    name if name is not None else old_name,
                    old_name if name_changed else None,
                    source_annotation,
                )
            except ConstraintError:
                raise EntityDuplicateError(name or old_name, existing["type"].lower())

        logger.info(
            "Entity updated",
            entity_id=entity_id,
            name_changed=name_changed,
            investigation_id=inv_id_str,
        )

        # Return fresh detail
        return await self.get_entity_detail(investigation_id, entity_id)

    async def preview_merge(
        self,
        investigation_id: uuid.UUID,
        source_entity_id: str,
        target_entity_id: str,
    ) -> EntityMergePreview | None:
        """Generate a merge preview showing combined relationships and sources.

        Returns None if either entity is not found.
        """
        source = await self.get_entity_detail(investigation_id, source_entity_id)
        target = await self.get_entity_detail(investigation_id, target_entity_id)
        if source is None or target is None:
            return None

        inv_id_str = str(investigation_id)

        # Find duplicate relationships (same type + same third party on both)
        async with self.neo4j_driver.session() as session:
            dup_records = await session.execute_read(
                _fetch_duplicate_relationships,
                source_entity_id,
                target_entity_id,
                inv_id_str,
            )

        duplicate_rels = [r["rel_type"] for r in dup_records]

        # Calculate totals after merge
        source_rel_types = {
            (r.relation_type, r.target_id) for r in source.relationships
        }
        target_rel_types = {
            (r.relation_type, r.target_id) for r in target.relationships
        }
        # Unique relationships = union (duplicates consolidated)
        total_rels = len(source_rel_types | target_rel_types)

        source_citations = {
            (s.document_id, s.chunk_id) for s in source.sources
        }
        target_citations = {
            (s.document_id, s.chunk_id) for s in target.sources
        }
        total_sources = len(source_citations | target_citations)

        return EntityMergePreview(
            source_entity=source,
            target_entity=target,
            duplicate_relationships=duplicate_rels,
            total_relationships_after=total_rels,
            total_sources_after=total_sources,
        )

    async def merge_entities(
        self,
        investigation_id: uuid.UUID,
        source_entity_id: str,
        target_entity_id: str,
        primary_name: str | None = None,
    ) -> EntityMergeResponse:
        """Merge source entity into target entity atomically.

        All relationships and provenance edges transfer from source to target.
        Duplicate relationships are consolidated (higher confidence wins).
        The source entity is deleted after transfer.
        """
        inv_id_str = str(investigation_id)

        async with self.neo4j_driver.session() as session:
            try:
                merge_counts = await session.execute_write(
                    _merge_entities_tx,
                    source_entity_id,
                    target_entity_id,
                    inv_id_str,
                    primary_name,
                )
            except Exception as exc:
                logger.error(
                    "Entity merge transaction failed",
                    source_entity_id=source_entity_id,
                    target_entity_id=target_entity_id,
                    investigation_id=inv_id_str,
                    error=str(exc),
                )
                raise EntityMergeError(f"Merge transaction failed: {exc}")

        # NOTE: Qdrant stores document chunk embeddings, not entity references.
        # Entity data lives exclusively in Neo4j. No Qdrant updates needed.
        logger.debug(
            "Qdrant update skipped — entities not stored in Qdrant",
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
        )

        # Fetch the updated merged entity detail
        merged_entity = await self.get_entity_detail(
            investigation_id, target_entity_id
        )
        if merged_entity is None:
            raise EntityMergeError("Merged entity not found after merge")

        logger.info(
            "Entity merge completed",
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            investigation_id=inv_id_str,
            relationships_transferred=merge_counts["rels_transferred"],
            citations_transferred=merge_counts["citations_transferred"],
            duplicates_consolidated=merge_counts["duplicates_consolidated"],
        )

        return EntityMergeResponse(
            merged_entity=merged_entity,
            relationships_transferred=merge_counts["rels_transferred"],
            citations_transferred=merge_counts["citations_transferred"],
            aliases_added=merge_counts["aliases_added"],
            duplicate_relationships_consolidated=merge_counts[
                "duplicates_consolidated"
            ],
        )

    async def get_entity_detail(
        self, investigation_id: uuid.UUID, entity_id: str
    ) -> EntityDetailResponse | None:
        """Return full entity detail with relationships and provenance sources.

        Returns None if entity not found or does not belong to the investigation.
        """
        inv_id_str = str(investigation_id)

        async with self.neo4j_driver.session() as session:
            entity_record = await session.execute_read(
                _fetch_entity, entity_id, inv_id_str
            )
            if entity_record is None:
                return None

            rels_data = await session.execute_read(
                _fetch_relationships, entity_id, inv_id_str
            )
            sources_data = await session.execute_read(
                _fetch_sources, entity_id, inv_id_str
            )

        # Enrich sources with document filenames from PostgreSQL
        doc_ids = list({s["document_id"] for s in sources_data})
        filename_map: dict[str, str] = {}
        if doc_ids:
            try:
                result = await self.db.execute(
                    select(Document.id, Document.filename).where(
                        Document.id.in_([uuid.UUID(d) for d in doc_ids])
                    )
                )
                filename_map = {str(row.id): row.filename for row in result}
            except Exception as exc:
                logger.warning(
                    "Failed to fetch document filenames for entity provenance",
                    entity_id=entity_id,
                    error=str(exc),
                )

        # Build response
        relationships = [
            EntityRelationship(
                relation_type=r["relation_type"],
                target_id=r.get("target_id"),
                target_name=r.get("target_name"),
                target_type=r.get("target_type"),
                confidence_score=r.get("confidence_score") or 0.0,
            )
            for r in rels_data
        ]

        sources = [
            EntitySource(
                document_id=s["document_id"],
                document_filename=filename_map.get(s["document_id"], "unknown"),
                chunk_id=s["chunk_id"],
                page_start=s["page_start"],
                page_end=s["page_end"],
                text_excerpt=s["text_excerpt"] or "",
            )
            for s in sources_data
        ]

        distinct_doc_count = len({s.document_id for s in sources})
        if distinct_doc_count >= 2:
            evidence_strength = "corroborated"
        elif distinct_doc_count == 1:
            evidence_strength = "single_source"
        else:
            evidence_strength = "none"

        return EntityDetailResponse(
            id=entity_record["id"],
            name=entity_record["name"],
            type=entity_record["type"].lower(),
            confidence_score=entity_record["confidence_score"],
            investigation_id=inv_id_str,
            relationships=relationships,
            sources=sources,
            evidence_strength=evidence_strength,
            source=entity_record.get("source") or "extracted",
            source_annotation=entity_record.get("source_annotation"),
            aliases=entity_record.get("aliases") or [],
        )


# ---------------------------------------------------------------------------
# Neo4j read transaction helpers
# ---------------------------------------------------------------------------

async def _fetch_entity_list(
    tx, investigation_id: str, entity_type: str | None, search: str | None = None
):
    """Fetch all entities for an investigation with source counts."""
    if entity_type:
        label = entity_type.capitalize()
        match_clause = f"MATCH (e:{label} {{investigation_id: $investigation_id}})"
    else:
        match_clause = "MATCH (e:Person|Organization|Location {investigation_id: $investigation_id})"

    where_clause = ""
    if search:
        where_clause = " WHERE toLower(e.name) CONTAINS toLower($search)"

    query = (
        f"{match_clause}"
        f"{where_clause} "
        "OPTIONAL MATCH (e)-[m:MENTIONED_IN]->(d:Document) "
        "WITH e, labels(e)[0] AS type, e.confidence_score AS confidence_score, "
        "COUNT(DISTINCT d) AS source_count "
        "RETURN e.id AS id, e.name AS name, type, confidence_score, source_count, "
        "e.source AS source"
    )
    params = {"investigation_id": investigation_id}
    if search:
        params["search"] = search
    result = await tx.run(query, **params)
    return await result.data()


async def _fetch_entity(tx, entity_id: str, investigation_id: str):
    """Fetch a single entity node by id and investigation_id."""
    result = await tx.run(
        "MATCH (e:Person|Organization|Location {id: $entity_id, investigation_id: $investigation_id}) "
        "RETURN e.id AS id, e.name AS name, labels(e)[0] AS type, "
        "e.confidence_score AS confidence_score, "
        "e.source AS source, e.source_annotation AS source_annotation, "
        "e.aliases AS aliases",
        entity_id=entity_id,
        investigation_id=investigation_id,
    )
    return await result.single()


async def _fetch_relationships(tx, entity_id: str, investigation_id: str):
    """Fetch outgoing entity-to-entity relationships."""
    result = await tx.run(
        "MATCH (e {id: $entity_id, investigation_id: $inv_id})"
        "-[r]->(t {investigation_id: $inv_id}) "
        "WHERE type(r) <> 'MENTIONED_IN' "
        "RETURN type(r) AS relation_type, t.id AS target_id, t.name AS target_name, "
        "labels(t)[0] AS target_type, r.confidence_score AS confidence_score",
        entity_id=entity_id,
        inv_id=investigation_id,
    )
    return await result.data()


async def _fetch_sources(tx, entity_id: str, investigation_id: str):
    """Fetch MENTIONED_IN provenance edges to Document nodes."""
    result = await tx.run(
        "MATCH (e {id: $entity_id, investigation_id: $inv_id})"
        "-[m:MENTIONED_IN]->(d:Document {investigation_id: $inv_id}) "
        "RETURN d.id AS document_id, m.chunk_id AS chunk_id, "
        "m.page_start AS page_start, m.page_end AS page_end, m.text_excerpt AS text_excerpt",
        entity_id=entity_id,
        inv_id=investigation_id,
    )
    return await result.data()


# ---------------------------------------------------------------------------
# Neo4j write transaction helpers
# ---------------------------------------------------------------------------


async def _create_entity(
    tx,
    entity_id: str,
    name: str,
    entity_type: str,
    investigation_id: str,
    source_annotation: str | None,
    label: str,
):
    """Create a manual entity node in Neo4j."""
    await tx.run(
        f"CREATE (e:{label} {{"
        "  id: $id, name: $name, type: $type,"
        "  investigation_id: $investigation_id,"
        "  confidence_score: 1.0, source: 'manual',"
        "  source_annotation: $source_annotation,"
        "  aliases: [], created_at: datetime()"
        "})",
        id=entity_id,
        name=name,
        type=entity_type,
        investigation_id=investigation_id,
        source_annotation=source_annotation,
    )


async def _update_entity(
    tx,
    entity_id: str,
    investigation_id: str,
    new_name: str,
    old_name_to_alias: str | None,
    source_annotation: str | None,
):
    """Update entity name and/or source_annotation, preserving aliases."""
    set_clauses = ["e.name = $new_name"]

    if old_name_to_alias is not None:
        set_clauses.append(
            "e.aliases = CASE WHEN $old_name IN COALESCE(e.aliases, []) "
            "THEN COALESCE(e.aliases, []) "
            "ELSE COALESCE(e.aliases, []) + [$old_name] END"
        )

    if source_annotation is not None:
        set_clauses.append("e.source_annotation = $source_annotation")

    query = (
        "MATCH (e:Person|Organization|Location "
        "{id: $entity_id, investigation_id: $investigation_id}) "
        f"SET {', '.join(set_clauses)}"
    )

    await tx.run(
        query,
        entity_id=entity_id,
        investigation_id=investigation_id,
        new_name=new_name,
        old_name=old_name_to_alias,
        source_annotation=source_annotation,
    )


# ---------------------------------------------------------------------------
# Neo4j merge transaction helpers
# ---------------------------------------------------------------------------


async def _fetch_duplicate_relationships(
    tx, source_id: str, target_id: str, investigation_id: str
):
    """Find relationships where both source and target entities connect
    to the same third party with the same relationship type (outgoing and incoming)."""
    # Outgoing duplicates: (source)-[r]->(o) AND (target)-[r]->(o)
    out_result = await tx.run(
        "MATCH (s {id: $sid, investigation_id: $inv})-[r1]->(o) "
        "WHERE type(r1) <> 'MENTIONED_IN' AND o.id <> $tid "
        "WITH o, type(r1) AS rel_type "
        "MATCH (t {id: $tid, investigation_id: $inv})-[r2]->(o) "
        "WHERE type(r2) = rel_type "
        "RETURN DISTINCT rel_type",
        sid=source_id,
        tid=target_id,
        inv=investigation_id,
    )
    out_data = await out_result.data()

    # Incoming duplicates: (o)-[r]->(source) AND (o)-[r]->(target)
    in_result = await tx.run(
        "MATCH (o)-[r1]->(s {id: $sid, investigation_id: $inv}) "
        "WHERE type(r1) <> 'MENTIONED_IN' AND o.id <> $tid "
        "WITH o, type(r1) AS rel_type "
        "MATCH (o)-[r2]->(t {id: $tid, investigation_id: $inv}) "
        "WHERE type(r2) = rel_type "
        "RETURN DISTINCT rel_type",
        sid=source_id,
        tid=target_id,
        inv=investigation_id,
    )
    in_data = await in_result.data()

    # Combine and deduplicate
    seen = set()
    combined = []
    for record in out_data + in_data:
        rt = record["rel_type"]
        if rt not in seen:
            seen.add(rt)
            combined.append(record)
    return combined


def _validate_rel_type(rtype: str) -> str:
    """Validate relationship type to prevent Cypher injection.

    Neo4j relationship types are UPPER_SNAKE_CASE by convention.
    Only allow alphanumeric characters and underscores.
    """
    import re

    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", rtype):
        raise ValueError(f"Invalid relationship type: {rtype}")
    return rtype


async def _merge_entities_tx(
    tx,
    source_id: str,
    target_id: str,
    investigation_id: str,
    primary_name: str | None,
):
    """Atomic merge: transfer relationships, citations, aliases, then delete source.

    All steps execute within a single Neo4j write transaction.
    Returns dict with counts of transferred items.
    """
    rels_transferred = 0
    citations_transferred = 0
    duplicates_consolidated = 0
    aliases_added: list[str] = []

    # --- Step A: Transfer outgoing relationships (source)-[r]->(other) ---
    out_result = await tx.run(
        "MATCH (s {id: $sid, investigation_id: $inv})-[r]->(o) "
        "WHERE type(r) <> 'MENTIONED_IN' AND o.id <> $tid "
        "RETURN type(r) AS rtype, o.id AS oid, "
        "r.confidence_score AS conf, r.source_chunk_id AS chunk_id",
        sid=source_id, tid=target_id, inv=investigation_id,
    )
    outgoing_rels = await out_result.data()

    for rel in outgoing_rels:
        rtype = _validate_rel_type(rel["rtype"])
        # Check if target already has this relationship
        existing_result = await tx.run(
            f"MATCH (t {{id: $tid}})-[r:{rtype}]->(o {{id: $oid}}) "
            "RETURN r.confidence_score AS conf",
            tid=target_id, oid=rel["oid"],
        )
        existing = await existing_result.single()
        if existing:
            # Duplicate — consolidate with higher confidence
            duplicates_consolidated += 1
            new_conf = rel["conf"] or 0.0
            old_conf = existing["conf"] or 0.0
            if new_conf > old_conf:
                await tx.run(
                    f"MATCH (t {{id: $tid}})-[r:{rtype}]->(o {{id: $oid}}) "
                    "SET r.confidence_score = $conf",
                    tid=target_id, oid=rel["oid"], conf=new_conf,
                )
        else:
            await tx.run(
                f"MATCH (t {{id: $tid, investigation_id: $inv}}), (o {{id: $oid}}) "
                f"CREATE (t)-[r:{rtype} {{confidence_score: $conf, "
                "source_chunk_id: $chunk_id}}]->(o)",
                tid=target_id, inv=investigation_id, oid=rel["oid"],
                conf=rel["conf"], chunk_id=rel.get("chunk_id"),
            )
            rels_transferred += 1

    # --- Step A (cont.): Transfer incoming relationships (other)-[r]->(source) ---
    in_result = await tx.run(
        "MATCH (o)-[r]->(s {id: $sid, investigation_id: $inv}) "
        "WHERE type(r) <> 'MENTIONED_IN' AND o.id <> $tid "
        "RETURN type(r) AS rtype, o.id AS oid, "
        "r.confidence_score AS conf, r.source_chunk_id AS chunk_id",
        sid=source_id, tid=target_id, inv=investigation_id,
    )
    incoming_rels = await in_result.data()

    for rel in incoming_rels:
        rtype = _validate_rel_type(rel["rtype"])
        existing_result = await tx.run(
            f"MATCH (o {{id: $oid}})-[r:{rtype}]->(t {{id: $tid}}) "
            "RETURN r.confidence_score AS conf",
            oid=rel["oid"], tid=target_id,
        )
        existing = await existing_result.single()
        if existing:
            duplicates_consolidated += 1
            new_conf = rel["conf"] or 0.0
            old_conf = existing["conf"] or 0.0
            if new_conf > old_conf:
                await tx.run(
                    f"MATCH (o {{id: $oid}})-[r:{rtype}]->(t {{id: $tid}}) "
                    "SET r.confidence_score = $conf",
                    oid=rel["oid"], tid=target_id, conf=new_conf,
                )
        else:
            await tx.run(
                f"MATCH (o {{id: $oid}}), (t {{id: $tid, investigation_id: $inv}}) "
                f"CREATE (o)-[r:{rtype} {{confidence_score: $conf, "
                "source_chunk_id: $chunk_id}}]->(t)",
                oid=rel["oid"], tid=target_id, inv=investigation_id,
                conf=rel["conf"], chunk_id=rel.get("chunk_id"),
            )
            rels_transferred += 1

    # --- Step C: Transfer MENTIONED_IN provenance edges ---
    mention_result = await tx.run(
        "MATCH (s {id: $sid, investigation_id: $inv})"
        "-[m:MENTIONED_IN]->(d:Document) "
        "RETURN d.id AS doc_id, m.chunk_id AS chunk_id, "
        "m.page_start AS page_start, m.page_end AS page_end, "
        "m.text_excerpt AS text_excerpt",
        sid=source_id, inv=investigation_id,
    )
    mentions = await mention_result.data()

    for mention in mentions:
        # Check if target already has this exact mention
        existing_mention = await tx.run(
            "MATCH (t {id: $tid})-[m:MENTIONED_IN {chunk_id: $chunk_id}]->"
            "(d:Document {id: $doc_id}) "
            "RETURN m",
            tid=target_id, chunk_id=mention["chunk_id"],
            doc_id=mention["doc_id"],
        )
        if await existing_mention.single() is None:
            await tx.run(
                "MATCH (t {id: $tid, investigation_id: $inv}), "
                "(d:Document {id: $doc_id, investigation_id: $inv}) "
                "CREATE (t)-[:MENTIONED_IN {"
                "chunk_id: $chunk_id, page_start: $page_start, "
                "page_end: $page_end, text_excerpt: $text_excerpt"
                "}]->(d)",
                tid=target_id, inv=investigation_id,
                doc_id=mention["doc_id"],
                chunk_id=mention["chunk_id"],
                page_start=mention["page_start"],
                page_end=mention["page_end"],
                text_excerpt=mention["text_excerpt"],
            )
            citations_transferred += 1

    # --- Step D: Update aliases, name, and source_annotation ---
    # Fetch current source and target metadata
    src_result = await tx.run(
        "MATCH (s {id: $sid, investigation_id: $inv}) "
        "RETURN s.name AS name, s.aliases AS aliases, "
        "s.source_annotation AS source_annotation",
        sid=source_id, inv=investigation_id,
    )
    src_record = await src_result.single()

    tgt_result = await tx.run(
        "MATCH (t {id: $tid, investigation_id: $inv}) "
        "RETURN t.name AS name, t.aliases AS aliases, "
        "t.source_annotation AS source_annotation",
        tid=target_id, inv=investigation_id,
    )
    tgt_record = await tgt_result.single()

    source_name = src_record["name"]
    source_aliases = src_record["aliases"] or []
    source_annotation = src_record["source_annotation"]
    target_name = tgt_record["name"]
    target_aliases = tgt_record["aliases"] or []
    target_annotation = tgt_record["source_annotation"]

    # Merge source annotations: append source's annotation to target's
    merged_annotation = target_annotation
    if source_annotation:
        if target_annotation:
            merged_annotation = f"{target_annotation}\n[Merged] {source_annotation}"
        else:
            merged_annotation = source_annotation

    # Build combined aliases list
    combined_aliases = list(target_aliases)
    # Add source name as alias if not already present
    if source_name not in combined_aliases and source_name != target_name:
        combined_aliases.append(source_name)
        aliases_added.append(source_name)
    # Add source aliases if not already present
    for alias in source_aliases:
        if alias not in combined_aliases and alias != target_name:
            combined_aliases.append(alias)
            aliases_added.append(alias)

    # Handle primary_name selection
    final_name = target_name
    if primary_name and primary_name != target_name:
        # Add the current target name as an alias since we're replacing it
        if target_name not in combined_aliases:
            combined_aliases.append(target_name)
            aliases_added.append(target_name)
        # Remove primary_name from aliases if it's there (it becomes the main name)
        combined_aliases = [a for a in combined_aliases if a != primary_name]
        final_name = primary_name

    # --- Step E: Update target's confidence, name, aliases, and annotation ---
    await tx.run(
        "MATCH (s {id: $sid, investigation_id: $inv}) "
        "MATCH (t {id: $tid, investigation_id: $inv}) "
        "SET t.confidence_score = CASE "
        "  WHEN s.confidence_score > t.confidence_score "
        "  THEN s.confidence_score ELSE t.confidence_score END, "
        "t.name = $final_name, "
        "t.aliases = $aliases, "
        "t.source_annotation = $annotation",
        sid=source_id, tid=target_id, inv=investigation_id,
        final_name=final_name, aliases=combined_aliases,
        annotation=merged_annotation,
    )

    # --- Step F: Delete source entity and all its remaining relationships ---
    await tx.run(
        "MATCH (s {id: $sid, investigation_id: $inv}) "
        "DETACH DELETE s",
        sid=source_id, inv=investigation_id,
    )

    return {
        "rels_transferred": rels_transferred,
        "citations_transferred": citations_transferred,
        "duplicates_consolidated": duplicates_consolidated,
        "aliases_added": aliases_added,
    }
