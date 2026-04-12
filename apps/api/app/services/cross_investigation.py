import time
import uuid

from loguru import logger
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

# Allowed entity type labels for Neo4j queries (prevents Cypher injection)
_ALLOWED_ENTITY_LABELS = {"Person", "Organization", "Location"}

from app.models.dismissed_match import DismissedMatch
from app.models.document import Document
from app.models.investigation import Investigation
from app.schemas.cross_investigation import (
    CrossInvestigationEntityDetail,
    CrossInvestigationMatch,
    CrossInvestigationResponse,
    CrossInvestigationSearchResponse,
    CrossInvestigationSearchResult,
    CrossInvestigationSearchResultInvestigation,
    EntityDocumentInfo,
    EntityRelationshipInfo,
    InvestigationEntityInfo,
    InvestigationPresence,
)


class CrossInvestigationService:
    def __init__(self, neo4j_driver, db: AsyncSession):
        self.neo4j_driver = neo4j_driver
        self.db = db

    # ------------------------------------------------------------------
    # Story 10.1: find_matches (updated to filter dismissed)
    # ------------------------------------------------------------------

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

        # Load dismissed matches for this investigation
        dismissed = await self._load_dismissed_matches(investigation_id)

        # Phase 3: Resolve investigation names from PostgreSQL
        matched_inv_ids = set()
        for record in raw_matches:
            matched_inv_ids.add(record["match_investigation_id"])

        inv_name_map = await self._resolve_investigation_names(matched_inv_ids)

        # Group by (entity_name, entity_type) to collect all matching investigations
        grouped: dict[tuple[str, str], dict] = {}
        for record in raw_matches:
            entity_type_lower = record["entity_type"].lower()
            match_inv_id = record["match_investigation_id"]

            # Skip dismissed matches
            if (record["entity_name"].lower(), entity_type_lower, match_inv_id) in dismissed:
                continue

            key = (record["entity_name"], entity_type_lower)
            if key not in grouped:
                # Determine match type based on exact name comparison
                is_exact = record.get("is_exact_match", False)
                grouped[key] = {
                    "entity_name": record["entity_name"],
                    "entity_type": entity_type_lower,
                    "match_confidence": 1.0 if is_exact else 0.9,
                    "match_type": "exact" if is_exact else "case_insensitive",
                    "source_entity_id": record["source_entity_id"],
                    "source_relationship_count": record["source_rel_count"],
                    "source_confidence_score": record.get("source_confidence") or 0.0,
                    "investigations": [],
                    "seen_inv_ids": set(),
                }

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
            if g["investigations"]  # Exclude entries with all investigations dismissed
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

    # ------------------------------------------------------------------
    # Story 10.2: Entity detail across investigations
    # ------------------------------------------------------------------

    async def get_entity_detail_across_investigations(
        self,
        entity_name: str,
        entity_type: str,
    ) -> CrossInvestigationEntityDetail:
        """Get full detail for an entity across all investigations."""
        start_time = time.monotonic()

        label = entity_type.capitalize()
        if label not in _ALLOWED_ENTITY_LABELS:
            return CrossInvestigationEntityDetail(
                entity_name=entity_name,
                entity_type=entity_type,
                investigations=[],
                total_investigations=0,
            )

        async with self.neo4j_driver.session() as session:
            raw_data = await session.execute_read(
                _fetch_entity_detail_across, entity_name, label
            )

        if not raw_data:
            return CrossInvestigationEntityDetail(
                entity_name=entity_name,
                entity_type=entity_type,
                investigations=[],
                total_investigations=0,
            )

        # Collect all investigation IDs and document IDs for batch resolution
        inv_ids = set()
        doc_ids = set()
        for record in raw_data:
            inv_ids.add(record["investigation_id"])
            for doc in record.get("documents") or []:
                if doc.get("document_id"):
                    doc_ids.add(doc["document_id"])

        inv_name_map = await self._resolve_investigation_names(inv_ids)
        doc_name_map = await self._resolve_document_filenames(doc_ids)

        # Build per-investigation presence data
        inv_data: dict[str, dict] = {}
        for record in raw_data:
            inv_id = record["investigation_id"]
            if inv_id not in inv_data:
                inv_data[inv_id] = {
                    "entity_id": record["entity_id"],
                    "confidence_score": record.get("confidence_score") or 0.0,
                    "relationships": [],
                    "documents": [],
                    "seen_rels": set(),
                    "seen_docs": set(),
                }

            for rel in record.get("relationships") or []:
                if rel and rel.get("type"):
                    rel_key = (rel["type"], rel.get("target_name", ""))
                    if rel_key not in inv_data[inv_id]["seen_rels"]:
                        inv_data[inv_id]["seen_rels"].add(rel_key)
                        inv_data[inv_id]["relationships"].append(
                            EntityRelationshipInfo(
                                type=rel["type"],
                                target_name=rel.get("target_name"),
                                target_type=(rel.get("target_type") or "").lower() or None,
                                confidence_score=rel.get("confidence") or 0.0,
                            )
                        )

            for doc in record.get("documents") or []:
                doc_id = doc.get("document_id")
                if doc_id and doc_id not in inv_data[inv_id]["seen_docs"]:
                    inv_data[inv_id]["seen_docs"].add(doc_id)
                    inv_data[inv_id]["documents"].append(
                        EntityDocumentInfo(
                            document_id=doc_id,
                            filename=doc_name_map.get(doc_id, "unknown"),
                            mention_count=doc.get("mention_count") or 1,
                        )
                    )

        investigations = [
            InvestigationPresence(
                investigation_id=inv_id,
                investigation_name=inv_name_map.get(inv_id, "Unknown Investigation"),
                entity_id=data["entity_id"],
                relationships=data["relationships"],
                source_documents=data["documents"],
                relationship_count=len(data["relationships"]),
                confidence_score=data["confidence_score"],
            )
            for inv_id, data in inv_data.items()
        ]

        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(
            "Cross-investigation entity detail loaded",
            entity_name=entity_name,
            entity_type=entity_type,
            investigation_count=len(investigations),
            duration_ms=round(duration_ms, 1),
        )

        return CrossInvestigationEntityDetail(
            entity_name=entity_name,
            entity_type=entity_type,
            investigations=investigations,
            total_investigations=len(investigations),
        )

    # ------------------------------------------------------------------
    # Story 10.2: Search across investigations
    # ------------------------------------------------------------------

    async def search_across_investigations(
        self,
        query: str,
        entity_type: str | None = None,
        limit: int = 20,
    ) -> CrossInvestigationSearchResponse:
        """Search for entities by name across all investigations."""
        start_time = time.monotonic()

        type_filter = None
        if entity_type:
            label = entity_type.capitalize()
            if label not in _ALLOWED_ENTITY_LABELS:
                duration_ms = (time.monotonic() - start_time) * 1000
                return CrossInvestigationSearchResponse(
                    results=[], total_results=0, query_duration_ms=round(duration_ms, 1)
                )
            type_filter = label

        async with self.neo4j_driver.session() as session:
            raw_results = await session.execute_read(
                _fetch_search_across_investigations, query, type_filter
            )

        if not raw_results:
            duration_ms = (time.monotonic() - start_time) * 1000
            return CrossInvestigationSearchResponse(
                results=[], total_results=0, query_duration_ms=round(duration_ms, 1)
            )

        # Collect investigation IDs for name resolution
        inv_ids = {r["investigation_id"] for r in raw_results}
        inv_name_map = await self._resolve_investigation_names(inv_ids)

        # Group by (entity_name_lower, entity_type)
        grouped: dict[tuple[str, str], dict] = {}
        for r in raw_results:
            key = (r["entity_name"].lower(), r["entity_type"].lower())
            if key not in grouped:
                grouped[key] = {
                    "entity_name": r["entity_name"],
                    "entity_type": r["entity_type"].lower(),
                    "investigations": [],
                    "seen_inv_ids": set(),
                }

            inv_id = r["investigation_id"]
            if inv_id not in grouped[key]["seen_inv_ids"]:
                grouped[key]["seen_inv_ids"].add(inv_id)
                grouped[key]["investigations"].append(
                    CrossInvestigationSearchResultInvestigation(
                        investigation_id=inv_id,
                        investigation_name=inv_name_map.get(inv_id, "Unknown"),
                        entity_id=r["entity_id"],
                        relationship_count=r.get("rel_count") or 0,
                    )
                )

        # Build results sorted by investigation_count DESC then name ASC
        results = [
            CrossInvestigationSearchResult(
                entity_name=g["entity_name"],
                entity_type=g["entity_type"],
                investigation_count=len(g["investigations"]),
                investigations=g["investigations"],
                match_score=1.0,
            )
            for g in grouped.values()
        ]
        results.sort(key=lambda r: (-r.investigation_count, r.entity_name.lower()))
        results = results[:limit]

        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(
            "Cross-investigation search complete",
            query=query,
            result_count=len(results),
            duration_ms=round(duration_ms, 1),
        )

        return CrossInvestigationSearchResponse(
            results=results,
            total_results=len(results),
            query_duration_ms=round(duration_ms, 1),
        )

    # ------------------------------------------------------------------
    # Story 10.2: Cross-link counts for investigation list
    # ------------------------------------------------------------------

    async def get_cross_link_counts(
        self,
        investigation_ids: list[str],
    ) -> dict[str, int]:
        """Get count of cross-investigation entity links per investigation."""
        if not investigation_ids:
            return {}

        async with self.neo4j_driver.session() as session:
            raw_counts = await session.execute_read(
                _fetch_cross_link_counts, investigation_ids
            )

        # Start with zero counts for all requested IDs
        counts: dict[str, int] = {inv_id: 0 for inv_id in investigation_ids}
        for record in raw_counts:
            inv_id = record["investigation_id"]
            counts[inv_id] = record["link_count"]

        # Subtract dismissed matches per investigation
        for inv_id in investigation_ids:
            try:
                dismissed_count = await self._count_dismissed_matches(
                    uuid.UUID(inv_id)
                )
                counts[inv_id] = max(0, counts[inv_id] - dismissed_count)
            except (ValueError, Exception):
                pass  # Keep the raw count if dismissal query fails

        return counts

    # ------------------------------------------------------------------
    # Story 10.2: Dismiss / undismiss matches
    # ------------------------------------------------------------------

    async def dismiss_match(
        self,
        source_investigation_id: uuid.UUID,
        entity_name: str,
        entity_type: str,
        target_investigation_id: uuid.UUID,
    ) -> bool:
        """Dismiss a cross-investigation match as false positive.

        Returns True if created, False if already exists.
        """
        from sqlalchemy.exc import IntegrityError

        dismissed = DismissedMatch(
            entity_name=entity_name,
            entity_type=entity_type,
            source_investigation_id=source_investigation_id,
            target_investigation_id=target_investigation_id,
        )
        self.db.add(dismissed)
        try:
            await self.db.flush()
            await self.db.commit()
            logger.info(
                "Cross-investigation match dismissed",
                entity_name=entity_name,
                entity_type=entity_type,
                source_investigation_id=str(source_investigation_id),
                target_investigation_id=str(target_investigation_id),
            )
            return True
        except IntegrityError:
            await self.db.rollback()
            return False

    async def undismiss_match(
        self,
        source_investigation_id: uuid.UUID,
        entity_name: str,
        entity_type: str,
        target_investigation_id: uuid.UUID,
    ) -> bool:
        """Remove a dismissed match (undo). Returns True if deleted."""
        result = await self.db.execute(
            select(DismissedMatch).where(
                DismissedMatch.entity_name == entity_name,
                DismissedMatch.entity_type == entity_type,
                DismissedMatch.source_investigation_id == source_investigation_id,
                DismissedMatch.target_investigation_id == target_investigation_id,
            )
        )
        dismissed = result.scalar_one_or_none()
        if dismissed is None:
            return False
        await self.db.delete(dismissed)
        await self.db.commit()
        logger.info(
            "Cross-investigation match undismissed",
            entity_name=entity_name,
            entity_type=entity_type,
            source_investigation_id=str(source_investigation_id),
            target_investigation_id=str(target_investigation_id),
        )
        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _load_dismissed_matches(
        self, investigation_id: uuid.UUID
    ) -> set[tuple[str, str, str]]:
        """Load dismissed matches as set of (entity_name_lower, entity_type, target_inv_id)."""
        try:
            result = await self.db.execute(
                select(
                    DismissedMatch.entity_name,
                    DismissedMatch.entity_type,
                    DismissedMatch.target_investigation_id,
                ).where(
                    DismissedMatch.source_investigation_id == investigation_id
                )
            )
            return {
                (row.entity_name.lower(), row.entity_type.lower(), str(row.target_investigation_id))
                for row in result
            }
        except Exception as exc:
            logger.warning("Failed to load dismissed matches", error=str(exc))
            return set()

    async def _count_dismissed_matches(
        self, investigation_id: uuid.UUID
    ) -> int:
        """Count distinct dismissed entity matches for an investigation."""
        try:
            result = await self.db.execute(
                select(sa_func.count(DismissedMatch.id)).where(
                    DismissedMatch.source_investigation_id == investigation_id
                )
            )
            return result.scalar_one()
        except Exception:
            return 0

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

    async def _resolve_document_filenames(
        self, document_ids: set[str]
    ) -> dict[str, str]:
        """Batch-fetch document filenames from PostgreSQL."""
        if not document_ids:
            return {}
        try:
            result = await self.db.execute(
                select(Document.id, Document.filename).where(
                    Document.id.in_([uuid.UUID(d) for d in document_ids])
                )
            )
            return {str(row.id): row.filename for row in result}
        except Exception as exc:
            logger.warning(
                "Failed to resolve document filenames",
                error=str(exc),
            )
            return {}


# ---------------------------------------------------------------------------
# Neo4j read transaction helpers
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


async def _fetch_entity_detail_across(tx, entity_name: str, entity_type_label: str):
    """Fetch full entity detail across all investigations for a name+type."""
    query = (
        f"MATCH (e:{entity_type_label}) "
        "WHERE toLower(e.name) = toLower($entity_name) "
        "WITH e "
        "OPTIONAL MATCH (e)-[r]->(t) WHERE type(r) <> 'MENTIONED_IN' "
        "WITH e, collect(DISTINCT {{ "
        "  type: type(r), target_name: t.name, "
        "  target_type: labels(t)[0], confidence: r.confidence_score "
        "}}) AS relationships "
        "OPTIONAL MATCH (e)-[:MENTIONED_IN]->(d:Document) "
        "WITH e, relationships, collect(DISTINCT {{ "
        "  document_id: d.id, mention_count: 1 "
        "}}) AS documents "
        "RETURN e.investigation_id AS investigation_id, e.id AS entity_id, "
        "  e.confidence_score AS confidence_score, "
        "  relationships, documents"
    )
    result = await tx.run(query, entity_name=entity_name)
    return await result.data()


async def _fetch_search_across_investigations(
    tx, query_text: str, entity_type_label: str | None
):
    """Search entities by name across all investigations."""
    if entity_type_label:
        match_clause = f"MATCH (e:{entity_type_label})"
    else:
        match_clause = "MATCH (e:Person|Organization|Location)"

    cypher = (
        f"{match_clause} "
        "WHERE toLower(e.name) CONTAINS toLower($query) "
        "OPTIONAL MATCH (e)-[r]->() WHERE type(r) <> 'MENTIONED_IN' "
        "WITH e, count(DISTINCT r) AS rel_count "
        "RETURN e.name AS entity_name, labels(e)[0] AS entity_type, "
        "  e.investigation_id AS investigation_id, e.id AS entity_id, "
        "  e.confidence_score AS confidence_score, rel_count "
        "ORDER BY e.name"
    )
    result = await tx.run(cypher, query=query_text)
    return await result.data()


async def _fetch_cross_link_counts(tx, investigation_ids: list[str]):
    """Count cross-investigation entity links per investigation."""
    query = (
        "UNWIND $investigation_ids AS inv_id "
        "MATCH (e1 {investigation_id: inv_id}) "
        "WHERE (e1:Person OR e1:Organization OR e1:Location) "
        "WITH inv_id, e1 "
        "MATCH (e2) "
        "WHERE (e2:Person OR e2:Organization OR e2:Location) "
        "  AND e2.investigation_id <> inv_id "
        "  AND toLower(e1.name) = toLower(e2.name) "
        "  AND labels(e1) = labels(e2) "
        "WITH inv_id, count(DISTINCT e1.name + '::' + labels(e1)[0]) AS link_count "
        "RETURN inv_id AS investigation_id, link_count"
    )
    result = await tx.run(query, investigation_ids=investigation_ids)
    return await result.data()
