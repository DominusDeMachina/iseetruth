from loguru import logger

from app.config import get_settings
from app.db.sync_postgres import SyncSessionLocal
from app.services.events import EventPublisher
from app.worker.celery_app import celery_app

settings = get_settings()


@celery_app.task(
    name="cross_investigation_match",
    acks_late=True,
    ignore_result=True,
)
def run_cross_investigation_match_task(
    investigation_id: str, document_id: str
) -> None:
    """Background task: find cross-investigation entity matches after extraction.

    Fire-and-forget — failures here must never affect document processing.
    """
    from neo4j import GraphDatabase

    _auth_parts = settings.neo4j_auth.split("/", 1)
    neo4j_driver = GraphDatabase.driver(
        settings.neo4j_uri, auth=(_auth_parts[0], _auth_parts[1])
    )

    publisher = EventPublisher(settings.celery_broker_url)

    try:
        with SyncSessionLocal() as session:
            raw_matches = _find_matches_sync(neo4j_driver, investigation_id)

            if not raw_matches:
                logger.debug(
                    "No cross-investigation matches found",
                    investigation_id=investigation_id,
                    document_id=document_id,
                )
                return

            # Resolve investigation names
            from sqlalchemy import select as sa_select
            from app.models.investigation import Investigation
            import uuid

            matched_inv_ids = {r["match_investigation_id"] for r in raw_matches}
            inv_result = session.execute(
                sa_select(Investigation.id, Investigation.name).where(
                    Investigation.id.in_(
                        [uuid.UUID(inv_id) for inv_id in matched_inv_ids]
                    )
                )
            )
            inv_name_map = {str(row.id): row.name for row in inv_result}

            # Group matches by entity
            grouped: dict[tuple[str, str], list[str]] = {}
            for record in raw_matches:
                key = (record["entity_name"], record["entity_type"].lower())
                inv_id = record["match_investigation_id"]
                if key not in grouped:
                    grouped[key] = []
                inv_name = inv_name_map.get(inv_id, "Unknown")
                if inv_name not in grouped[key]:
                    grouped[key].append(inv_name)

            new_matches = [
                {
                    "entity_name": name,
                    "entity_type": etype,
                    "matched_investigations": inv_names,
                }
                for (name, etype), inv_names in grouped.items()
            ]

            # Publish SSE event
            try:
                publisher.publish(
                    investigation_id=investigation_id,
                    event_type="cross_investigation.matches_found",
                    payload={
                        "match_count": len(new_matches),
                        "new_matches": new_matches,
                    },
                )
            except Exception as pub_exc:
                logger.warning(
                    "Failed to publish cross-investigation SSE event",
                    investigation_id=investigation_id,
                    error=str(pub_exc),
                )

            logger.info(
                "Cross-investigation matching complete",
                investigation_id=investigation_id,
                document_id=document_id,
                match_count=len(new_matches),
            )

    except Exception as exc:
        logger.warning(
            "Cross-investigation matching failed (non-fatal)",
            investigation_id=investigation_id,
            document_id=document_id,
            error=str(exc),
        )
    finally:
        neo4j_driver.close()


def _find_matches_sync(neo4j_driver, investigation_id: str) -> list[dict]:
    """Synchronous Neo4j query for cross-investigation entity matching."""
    query = (
        "MATCH (e1:Person|Organization|Location {investigation_id: $investigation_id}) "
        "WITH e1 "
        "MATCH (e2:Person|Organization|Location) "
        "WHERE e2.investigation_id <> $investigation_id "
        "  AND toLower(e1.name) = toLower(e2.name) "
        "  AND labels(e1) = labels(e2) "
        "RETURN e1.name AS entity_name, labels(e1)[0] AS entity_type, "
        "  e2.id AS match_entity_id, e2.investigation_id AS match_investigation_id"
    )
    with neo4j_driver.session() as session:
        result = session.run(query, investigation_id=investigation_id)
        return [dict(record) for record in result]
