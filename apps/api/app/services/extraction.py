import json
import uuid
from dataclasses import dataclass
from typing import Callable

from loguru import logger
from pydantic import ValidationError

from app.llm.client import DEFAULT_MODEL, OllamaClient
from app.llm.prompts import (
    ENTITY_EXTRACTION_SYSTEM_PROMPT,
    ENTITY_EXTRACTION_USER_PROMPT_TEMPLATE,
    RELATIONSHIP_EXTRACTION_SYSTEM_PROMPT,
    RELATIONSHIP_EXTRACTION_USER_PROMPT_TEMPLATE,
)
from app.llm.schemas import (
    EntityExtractionResponse,
    ExtractedEntity,
    ExtractedRelationship,
    RelationshipExtractionResponse,
)


@dataclass
class ExtractionSummary:
    entity_count: int
    relationship_count: int
    chunk_count: int
    average_confidence: float = 0.0


class EntityExtractionService:
    def __init__(self, ollama_client: OllamaClient, neo4j_driver):
        self.ollama_client = ollama_client
        self.neo4j_driver = neo4j_driver

    def extract_from_chunks(
        self,
        chunks: list,
        investigation_id: uuid.UUID,
        on_entity_discovered: Callable | None = None,
        on_chunk_progress: Callable[[int, int], None] | None = None,
    ) -> ExtractionSummary:
        """Extract entities and relationships from all chunks, storing results in Neo4j."""
        seen_entities: set[tuple[str, str]] = set()
        entity_confidences: dict[tuple[str, str], float] = {}
        total_relationship_count = 0

        for chunk_idx, chunk in enumerate(chunks):
            entities = self._extract_entities(chunk)
            relationships = self._extract_relationships(chunk, entities)
            self._store_in_neo4j(chunk, entities, relationships, investigation_id)

            for entity in entities:
                key = (entity.name, entity.type.value)
                existing = entity_confidences.get(key, 0.0)
                entity_confidences[key] = max(existing, entity.confidence)
                if key not in seen_entities:
                    seen_entities.add(key)
                    if on_entity_discovered is not None:
                        on_entity_discovered(entity)

            total_relationship_count += len(relationships)

            if on_chunk_progress is not None:
                on_chunk_progress(chunk_idx + 1, len(chunks))

        avg_confidence = (
            (sum(entity_confidences.values()) / len(entity_confidences))
            if entity_confidences
            else 0.0
        )

        return ExtractionSummary(
            entity_count=len(seen_entities),
            relationship_count=total_relationship_count,
            chunk_count=len(chunks),
            average_confidence=avg_confidence,
        )

    def _extract_entities(self, chunk) -> list[ExtractedEntity]:
        """Phase 1: call Ollama to extract Person/Organization/Location entities from chunk."""
        messages = [
            {"role": "system", "content": ENTITY_EXTRACTION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": ENTITY_EXTRACTION_USER_PROMPT_TEMPLATE.format(
                    chunk_text=chunk.text
                ),
            },
        ]
        try:
            response = self.ollama_client.chat(
                model=DEFAULT_MODEL, messages=messages, format="json", temperature=0
            )
            raw_content = response["message"]["content"]
            data = json.loads(raw_content)
            result = EntityExtractionResponse.model_validate(data)
            return result.entities
        except (KeyError, json.JSONDecodeError, ValidationError) as exc:
            logger.warning(
                "LLM response parse failed for entity extraction",
                chunk_id=str(chunk.id),
                error=str(exc),
            )
            return []

    def _extract_relationships(
        self, chunk, entities: list[ExtractedEntity]
    ) -> list[ExtractedRelationship]:
        """Phase 2: call Ollama to detect relationships between extracted entities."""
        if len(entities) < 2:
            return []

        entities_json = json.dumps(
            [{"name": e.name, "type": e.type.value} for e in entities]
        )
        messages = [
            {"role": "system", "content": RELATIONSHIP_EXTRACTION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": RELATIONSHIP_EXTRACTION_USER_PROMPT_TEMPLATE.format(
                    chunk_text=chunk.text, entities_json=entities_json
                ),
            },
        ]
        try:
            response = self.ollama_client.chat(
                model=DEFAULT_MODEL, messages=messages, format="json", temperature=0
            )
            raw_content = response["message"]["content"]
            data = json.loads(raw_content)
            result = RelationshipExtractionResponse.model_validate(data)

            # Validate referential integrity — only keep relationships between known entities
            entity_names = {e.name for e in entities}
            return [
                r
                for r in result.relationships
                if r.source_entity_name in entity_names
                and r.target_entity_name in entity_names
            ]
        except (KeyError, json.JSONDecodeError, ValidationError) as exc:
            logger.warning(
                "LLM response parse failed for relationship extraction",
                chunk_id=str(chunk.id),
                error=str(exc),
            )
            return []

    def _store_in_neo4j(
        self,
        chunk,
        entities: list[ExtractedEntity],
        relationships: list[ExtractedRelationship],
        investigation_id: uuid.UUID,
    ) -> None:
        """Atomically store entities, relationships, and provenance edges in Neo4j."""
        if not entities and not relationships:
            return

        entity_type_map = {e.name: e.type.value.capitalize() for e in entities}
        inv_id_str = str(investigation_id)
        doc_id_str = str(chunk.document_id)
        chunk_id_str = str(chunk.id)
        text_excerpt = chunk.text[:500]

        with self.neo4j_driver.session() as session:
            def _write_tx(tx):
                # --- Phase 1: MERGE entity nodes ---
                for entity in entities:
                    label = entity.type.value.capitalize()
                    tx.run(
                        f"MERGE (e:{label} {{name: $name, type: $type, investigation_id: $investigation_id}}) "
                        "ON CREATE SET e.id = $id, e.confidence_score = $confidence, e.created_at = datetime() "
                        "ON MATCH SET e.confidence_score = CASE WHEN $confidence > e.confidence_score "
                        "THEN $confidence ELSE e.confidence_score END",
                        name=entity.name,
                        type=entity.type.value,
                        investigation_id=inv_id_str,
                        id=str(uuid.uuid4()),
                        confidence=entity.confidence,
                    )

                # --- Phase 2: MERGE Document node + MENTIONED_IN provenance edges ---
                if entities:
                    tx.run(
                        "MERGE (d:Document {id: $doc_id, investigation_id: $inv_id})",
                        doc_id=doc_id_str,
                        inv_id=inv_id_str,
                    )
                for entity in entities:
                    label = entity.type.value.capitalize()
                    tx.run(
                        f"MATCH (e:{label} {{name: $name, investigation_id: $inv_id}}) "
                        "MATCH (d:Document {id: $doc_id, investigation_id: $inv_id}) "
                        "MERGE (e)-[m:MENTIONED_IN {chunk_id: $chunk_id}]->(d) "
                        "ON CREATE SET m.page_start = $page_start, m.page_end = $page_end, "
                        "m.text_excerpt = $text_excerpt",
                        name=entity.name,
                        inv_id=inv_id_str,
                        doc_id=doc_id_str,
                        chunk_id=chunk_id_str,
                        page_start=chunk.page_start,
                        page_end=chunk.page_end,
                        text_excerpt=text_excerpt,
                    )

                # --- Phase 3: MERGE entity-to-entity relationship edges ---
                for rel in relationships:
                    src_label = entity_type_map.get(rel.source_entity_name)
                    tgt_label = entity_type_map.get(rel.target_entity_name)
                    if src_label is None or tgt_label is None:
                        continue
                    rel_type = rel.relation_type
                    tx.run(
                        f"MATCH (src:{src_label} {{name: $src_name, investigation_id: $inv_id}}) "
                        f"MATCH (tgt:{tgt_label} {{name: $tgt_name, investigation_id: $inv_id}}) "
                        f"MERGE (src)-[r:{rel_type}]->(tgt) "
                        "ON CREATE SET r.confidence_score = $confidence, r.source_chunk_id = $chunk_id "
                        "ON MATCH SET r.confidence_score = CASE WHEN $confidence > r.confidence_score "
                        "THEN $confidence ELSE r.confidence_score END",
                        src_name=rel.source_entity_name,
                        tgt_name=rel.target_entity_name,
                        inv_id=inv_id_str,
                        confidence=rel.confidence,
                        chunk_id=chunk_id_str,
                    )

            session.execute_write(_write_tx)


def ensure_neo4j_constraints(driver) -> None:
    """Create uniqueness constraints and indexes for Neo4j entity and document nodes.

    Idempotent — safe to call on every deploy.
    """
    with driver.session() as session:
        # Entity uniqueness constraints (name, type, investigation_id)
        for label in ("Person", "Organization", "Location"):
            session.run(
                f"CREATE CONSTRAINT {label.lower()}_unique IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE (n.name, n.type, n.investigation_id) IS UNIQUE"
            )
        # Entity investigation_id indexes (fast per-investigation queries)
        for label in ("Person", "Organization", "Location"):
            session.run(
                f"CREATE INDEX entity_investigation_idx_{label.lower()} IF NOT EXISTS "
                f"FOR (n:{label}) ON (n.investigation_id)"
            )
        # Entity id indexes (fast API lookup by UUID)
        for label in ("Person", "Organization", "Location"):
            session.run(
                f"CREATE INDEX entity_id_idx_{label.lower()} IF NOT EXISTS "
                f"FOR (n:{label}) ON (n.id)"
            )
        # Document uniqueness constraint (id, investigation_id)
        session.run(
            "CREATE CONSTRAINT document_unique IF NOT EXISTS "
            "FOR (n:Document) REQUIRE (n.id, n.investigation_id) IS UNIQUE"
        )
        # Document investigation_id index
        session.run(
            "CREATE INDEX document_investigation_idx IF NOT EXISTS "
            "FOR (n:Document) ON (n.investigation_id)"
        )
