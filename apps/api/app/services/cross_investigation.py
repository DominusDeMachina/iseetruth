import time
import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.investigation import Investigation
from app.schemas.cross_investigation import (
    CrossInvestigationMatch,
    CrossInvestigationResponse,
    InvestigationEntityInfo,
)


class CrossInvestigationService:
    def __init__(self, neo4j_driver, db: AsyncSession):
        self.neo4j_driver = neo4j_driver
        self.db = db

    async def find_matches(
        self, investigation_id: uuid.UUID
    ) -> CrossInvestigationResponse:
        """Find entities in other investigations matching by name + type."""
        start_time = time.monotonic()
        inv_id_str = str(investigation_id)

        # Phase 1 & 2: Neo4j cross-investigation entity matching with relationship counts
        async with self.neo4j_driver.session() as session:
            raw_matches = await session.execute_read(
                _fetch_cross_investigation_matches, inv_id_str
            )

        if not raw_matches:
            duration_ms = (time.monotonic() - start_time) * 1000
            return CrossInvestigationResponse(
                matches=[], total_matches=0, query_duration_ms=round(duration_ms, 1)
            )

        # Phase 3: Resolve investigation names from PostgreSQL
        matched_inv_ids = set()
        for record in raw_matches:
            matched_inv_ids.add(record["match_investigation_id"])

        inv_name_map = await self._resolve_investigation_names(matched_inv_ids)

        # Group by (entity_name, entity_type) to collect all matching investigations
        grouped: dict[tuple[str, str], dict] = {}
        for record in raw_matches:
            key = (record["entity_name"], record["entity_type"].lower())
            if key not in grouped:
                # Determine match type based on exact name comparison
                is_exact = record.get("is_exact_match", False)
                grouped[key] = {
                    "entity_name": record["entity_name"],
                    "entity_type": record["entity_type"].lower(),
                    "match_confidence": 1.0 if is_exact else 0.9,
                    "match_type": "exact" if is_exact else "case_insensitive",
                    "source_entity_id": record["source_entity_id"],
                    "source_relationship_count": record["source_rel_count"],
                    "source_confidence_score": record.get("source_confidence") or 0.0,
                    "investigations": [],
                    "seen_inv_ids": set(),
                }

            match_inv_id = record["match_investigation_id"]
            if match_inv_id not in grouped[key]["seen_inv_ids"]:
                grouped[key]["seen_inv_ids"].add(match_inv_id)
                grouped[key]["investigations"].append(
                    InvestigationEntityInfo(
                        investigation_id=match_inv_id,
                        investigation_name=inv_name_map.get(
                            match_inv_id, "Unknown Investigation"
                        ),
                        entity_id=record["match_entity_id"],
                        relationship_count=record["match_rel_count"],
                        confidence_score=record.get("match_confidence") or 0.0,
                    )
                )

        # Build response sorted by confidence descending
        matches = [
            CrossInvestigationMatch(
                entity_name=g["entity_name"],
                entity_type=g["entity_type"],
                match_confidence=g["match_confidence"],
                match_type=g["match_type"],
                source_entity_id=g["source_entity_id"],
                source_relationship_count=g["source_relationship_count"],
                source_confidence_score=g["source_confidence_score"],
                investigations=g["investigations"],
            )
            for g in grouped.values()
        ]
        matches.sort(key=lambda m: m.match_confidence, reverse=True)

        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(
            "Cross-investigation matching complete",
            investigation_id=inv_id_str,
            match_count=len(matches),
            duration_ms=round(duration_ms, 1),
        )

        return CrossInvestigationResponse(
            matches=matches,
            total_matches=len(matches),
            query_duration_ms=round(duration_ms, 1),
        )

    async def _resolve_investigation_names(
        self, investigation_ids: set[str]
    ) -> dict[str, str]:
        """Batch-fetch investigation names from PostgreSQL."""
        if not investigation_ids:
            return {}
        try:
            result = await self.db.execute(
                select(Investigation.id, Investigation.name).where(
                    Investigation.id.in_(
                        [uuid.UUID(inv_id) for inv_id in investigation_ids]
                    )
                )
            )
            return {str(row.id): row.name for row in result}
        except Exception as exc:
            logger.warning(
                "Failed to resolve investigation names",
                error=str(exc),
            )
            return {}


# ---------------------------------------------------------------------------
# Neo4j read transaction helper
# ---------------------------------------------------------------------------

async def _fetch_cross_investigation_matches(tx, investigation_id: str):
    """Find entities in other investigations matching by name + type."""
    query = (
        "MATCH (e1:Person|Organization|Location {investigation_id: $investigation_id}) "
        "WITH e1 "
        "MATCH (e2:Person|Organization|Location) "
        "WHERE e2.investigation_id <> $investigation_id "
        "  AND toLower(e1.name) = toLower(e2.name) "
        "  AND labels(e1) = labels(e2) "
        "WITH e1, e2, e1.name = e2.name AS is_exact_match "
        "OPTIONAL MATCH (e1)-[r1]->() WHERE type(r1) <> 'MENTIONED_IN' "
        "WITH e1, e2, is_exact_match, count(DISTINCT r1) AS source_rel_count "
        "OPTIONAL MATCH (e2)-[r2]->() WHERE type(r2) <> 'MENTIONED_IN' "
        "RETURN e1.name AS entity_name, labels(e1)[0] AS entity_type, "
        "  e1.id AS source_entity_id, e1.confidence_score AS source_confidence, "
        "  source_rel_count, "
        "  e2.id AS match_entity_id, e2.investigation_id AS match_investigation_id, "
        "  e2.confidence_score AS match_confidence, "
        "  count(DISTINCT r2) AS match_rel_count, "
        "  is_exact_match"
    )
    result = await tx.run(query, investigation_id=investigation_id)
    return await result.data()
