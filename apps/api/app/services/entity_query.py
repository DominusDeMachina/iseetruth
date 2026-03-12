import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.schemas.entity import EntityDetailResponse, EntityRelationship, EntitySource


class EntityQueryService:
    def __init__(self, neo4j_driver, db: AsyncSession):
        self.neo4j_driver = neo4j_driver
        self.db = db

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
        )


# ---------------------------------------------------------------------------
# Neo4j read transaction helpers
# ---------------------------------------------------------------------------

async def _fetch_entity(tx, entity_id: str, investigation_id: str):
    """Fetch a single entity node by id and investigation_id."""
    result = await tx.run(
        "MATCH (e:Person|Organization|Location {id: $entity_id, investigation_id: $investigation_id}) "
        "RETURN e.id AS id, e.name AS name, labels(e)[0] AS type, "
        "e.confidence_score AS confidence_score",
        entity_id=entity_id,
        investigation_id=investigation_id,
    )
    return await result.single()


async def _fetch_relationships(tx, entity_id: str, investigation_id: str):
    """Fetch outgoing entity-to-entity relationships."""
    result = await tx.run(
        "MATCH (e {id: $entity_id, investigation_id: $inv_id})"
        "-[r:WORKS_FOR|KNOWS|LOCATED_AT]->(t {investigation_id: $inv_id}) "
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
