import json
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.config import get_settings
from app.db.neo4j import driver as neo4j_driver
from app.db.postgres import get_db
from app.db.qdrant import get_client as get_qdrant_client
from app.exceptions import DomainError
from app.llm.client import OllamaClient
from app.llm.embeddings import OllamaEmbeddingClient
from app.models.investigation import Investigation
from app.schemas.query import QueryRequest
from app.services.events import EventPublisher
from app.services.query import execute_query

router = APIRouter(prefix="/investigations", tags=["query"])

settings = get_settings()


@router.post("/{investigation_id}/query/")
async def query_investigation(
    investigation_id: uuid.UUID,
    body: QueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """Execute a natural language query against an investigation's knowledge graph.

    Returns an SSE stream with query pipeline events.
    """
    # Validate investigation exists
    result = await db.execute(
        select(Investigation).where(Investigation.id == investigation_id)
    )
    investigation = result.scalar_one_or_none()
    if investigation is None:
        raise DomainError(
            detail=f"No investigation found with id: {investigation_id}",
            status_code=404,
            error_type="investigation_not_found",
        )

    inv_id_str = str(investigation_id)
    query_id = str(uuid.uuid4())

    ollama_client = OllamaClient(settings.ollama_base_url)
    embedding_client = OllamaEmbeddingClient(settings.ollama_embedding_url)
    qdrant_client = get_qdrant_client()
    event_publisher = EventPublisher(settings.redis_url)

    conversation_history = None
    if body.conversation_history:
        conversation_history = [
            {"role": turn.role, "content": turn.content}
            for turn in body.conversation_history
        ]

    async def event_generator():
        try:
            async for sse_event in execute_query(
                investigation_id=inv_id_str,
                question=body.question,
                conversation_history=conversation_history,
                neo4j_driver=neo4j_driver,
                qdrant_client=qdrant_client,
                ollama_client=ollama_client,
                embedding_client=embedding_client,
                event_publisher=event_publisher,
                db=db,
                query_id=query_id,
            ):
                yield {
                    "event": sse_event["event"],
                    "data": json.dumps(sse_event["data"]),
                }
        except Exception:
            # Service already yields query.failed event before re-raising
            pass
        finally:
            event_publisher.close()

    return EventSourceResponse(event_generator())
