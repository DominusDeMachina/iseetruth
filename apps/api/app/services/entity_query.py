import uuid

from loguru import logger
from neo4j.exceptions import ConstraintError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import EntityDuplicateError, EntityNotFoundError
from app.models.document import Document
from app.schemas.entity import (
    EntityDetailResponse,
    EntityListItem,
    EntityListResponse,
    EntityRelationship,
    EntitySource,
    EntityTypeSummary,
)
from app.schemas.relationship import RelationshipResponse


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

    async def create_relationship(
        self,
        investigation_id: uuid.UUID,
        source_entity_id: str,
        target_entity_id: str,
        rel_type: str,
        source_annotation: str | None = None,
    ) -> RelationshipResponse:
        """Create a manual relationship between two entities in Neo4j.

        Returns existing relationship with already_existed=True if a duplicate is found.
        Raises EntityNotFoundError if either entity does not exist.
        """
        inv_id_str = str(investigation_id)

        async with self.neo4j_driver.session() as session:
            # Verify both entities exist
            source_entity = await session.execute_read(
                _fetch_entity, source_entity_id, inv_id_str
            )
            if source_entity is None:
                raise EntityNotFoundError(source_entity_id)

            target_entity = await session.execute_read(
                _fetch_entity, target_entity_id, inv_id_str
            )
            if target_entity is None:
                raise EntityNotFoundError(target_entity_id)

            # Check for existing duplicate
            existing = await session.execute_read(
                _fetch_existing_relationship,
                source_entity_id,
                target_entity_id,
                rel_type,
                inv_id_str,
            )
            if existing is not None:
                logger.info(
                    "Duplicate relationship found, returning existing",
                    source_entity_id=source_entity_id,
                    target_entity_id=target_entity_id,
                    type=rel_type,
                    investigation_id=inv_id_str,
                )
                return RelationshipResponse(
                    id=existing.get("id") or f"{source_entity_id}-{rel_type}-{target_entity_id}",
                    source_entity_id=source_entity_id,
                    target_entity_id=target_entity_id,
                    source_entity_name=source_entity["name"],
                    target_entity_name=target_entity["name"],
                    type=rel_type,
                    confidence_score=existing.get("confidence_score") or 0.0,
                    source=existing.get("source") or "extracted",
                    source_annotation=existing.get("source_annotation"),
                    already_existed=True,
                )

            # Create new relationship
            relationship_id = str(uuid.uuid4())
            await session.execute_write(
                _create_relationship,
                source_entity_id,
                target_entity_id,
                rel_type,
                relationship_id,
                source_annotation,
                inv_id_str,
            )

        logger.info(
            "Manual relationship created",
            relationship_id=relationship_id,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            type=rel_type,
            investigation_id=inv_id_str,
        )

        return RelationshipResponse(
            id=relationship_id,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            source_entity_name=source_entity["name"],
            target_entity_name=target_entity["name"],
            type=rel_type,
            confidence_score=1.0,
            source="manual",
            source_annotation=source_annotation,
            already_existed=False,
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


async def _fetch_existing_relationship(
    tx,
    source_entity_id: str,
    target_entity_id: str,
    rel_type: str,
    investigation_id: str,
):
    """Check if a relationship of the given type already exists between two entities."""
    # Dynamic relationship type in Cypher (safe: validated upstream as UPPER_SNAKE_CASE)
    query = (
        "MATCH (src:Person|Organization|Location "
        "{id: $source_id, investigation_id: $inv_id})"
        f"-[r:{rel_type}]->"
        "(tgt:Person|Organization|Location "
        "{id: $target_id, investigation_id: $inv_id}) "
        "RETURN r.id AS id, r.confidence_score AS confidence_score, "
        "r.source AS source, r.source_annotation AS source_annotation"
    )
    result = await tx.run(
        query,
        source_id=source_entity_id,
        target_id=target_entity_id,
        inv_id=investigation_id,
    )
    return await result.single()


async def _create_relationship(
    tx,
    source_entity_id: str,
    target_entity_id: str,
    rel_type: str,
    relationship_id: str,
    source_annotation: str | None,
    investigation_id: str,
):
    """Create a manual relationship between two entity nodes in Neo4j."""
    # Dynamic relationship type in Cypher (safe: validated upstream as UPPER_SNAKE_CASE)
    query = (
        "MATCH (src:Person|Organization|Location "
        "{id: $source_id, investigation_id: $inv_id}) "
        "MATCH (tgt:Person|Organization|Location "
        "{id: $target_id, investigation_id: $inv_id}) "
        f"CREATE (src)-[r:{rel_type} {{"
        "  id: $rel_id,"
        "  confidence_score: 1.0,"
        "  source: 'manual',"
        "  source_annotation: $source_annotation,"
        "  created_at: datetime()"
        "}]->(tgt)"
    )
    await tx.run(
        query,
        source_id=source_entity_id,
        target_id=target_entity_id,
        inv_id=investigation_id,
        rel_id=relationship_id,
        source_annotation=source_annotation,
    )
