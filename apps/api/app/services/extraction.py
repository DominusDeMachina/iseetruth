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


class EntityExtractionService:
    def __init__(self, ollama_client: OllamaClient, neo4j_driver):
        self.ollama_client = ollama_client
        self.neo4j_driver = neo4j_driver

    def extract_from_chunks(
        self,
        chunks: list,
        investigation_id: uuid.UUID,
        on_entity_discovered: Callable | None = None,
    ) -> ExtractionSummary:
        """Extract entities and relationships from all chunks, storing results in Neo4j."""
        seen_entities: set[tuple[str, str]] = set()
        total_relationship_count = 0

        for chunk in chunks:
            entities = self._extract_entities(chunk)
            relationships = self._extract_relationships(chunk, entities)
            self._store_in_neo4j(chunk, entities, relationships, investigation_id)

            for entity in entities:
                key = (entity.name, entity.type.value)
                if key not in seen_entities:
                    seen_entities.add(key)
                    if on_entity_discovered is not None:
                        on_entity_discovered(entity)

            total_relationship_count += len(relationships)

        return ExtractionSummary(
            entity_count=len(seen_entities),
            relationship_count=total_relationship_count,
            chunk_count=len(chunks),
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
        """Atomically store entities and relationships in Neo4j using MERGE."""
        if not entities and not relationships:
            return

        entity_type_map = {e.name: e.type.value.capitalize() for e in entities}

        with self.neo4j_driver.session() as session:
            def _write_tx(tx):
                for entity in entities:
                    label = entity.type.value.capitalize()
                    tx.run(
                        f"MERGE (e:{label} {{name: $name, type: $type, investigation_id: $investigation_id}}) "
                        "ON CREATE SET e.id = $id, e.confidence_score = $confidence, e.created_at = datetime() "
                        "ON MATCH SET e.confidence_score = CASE WHEN $confidence > e.confidence_score "
                        "THEN $confidence ELSE e.confidence_score END",
                        name=entity.name,
                        type=entity.type.value,
                        investigation_id=str(investigation_id),
                        id=str(uuid.uuid4()),
                        confidence=entity.confidence,
                    )

                for rel in relationships:
                    src_label = entity_type_map.get(rel.source_entity_name)
                    tgt_label = entity_type_map.get(rel.target_entity_name)
                    if src_label is None or tgt_label is None:
                        continue
                    rel_type = rel.relation_type.value
                    tx.run(
                        f"MATCH (src:{src_label} {{name: $src_name, investigation_id: $inv_id}}) "
                        f"MATCH (tgt:{tgt_label} {{name: $tgt_name, investigation_id: $inv_id}}) "
                        f"MERGE (src)-[r:{rel_type}]->(tgt) "
                        "ON CREATE SET r.confidence_score = $confidence, r.source_chunk_id = $chunk_id "
                        "ON MATCH SET r.confidence_score = CASE WHEN $confidence > r.confidence_score "
                        "THEN $confidence ELSE r.confidence_score END",
                        src_name=rel.source_entity_name,
                        tgt_name=rel.target_entity_name,
                        inv_id=str(investigation_id),
                        confidence=rel.confidence,
                        chunk_id=str(chunk.id),
                    )

            session.execute_write(_write_tx)


def ensure_neo4j_constraints(driver) -> None:
    """Create uniqueness constraints and investigation_id indexes for Neo4j entity nodes.

    Idempotent — safe to call on every deploy.
    """
    with driver.session() as session:
        for label in ("Person", "Organization", "Location"):
            session.run(
                f"CREATE CONSTRAINT {label.lower()}_unique IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE (n.name, n.type, n.investigation_id) IS UNIQUE"
            )
        for label in ("Person", "Organization", "Location"):
            session.run(
                f"CREATE INDEX entity_investigation_idx_{label.lower()} IF NOT EXISTS "
                f"FOR (n:{label}) ON (n.investigation_id)"
            )
