from fastapi import APIRouter

from app.api.v1.chunks import router as chunks_router
from app.api.v1.cross_investigation import cross_links_router, router as cross_investigation_router
from app.api.v1.documents import router as documents_router
from app.api.v1.entities import router as entities_router
from app.api.v1.events import router as events_router, system_router as system_events_router
from app.api.v1.graph import router as graph_router
from app.api.v1.health import router as health_router
from app.api.v1.investigations import router as investigations_router
from app.api.v1.query import router as query_router
from app.api.v1.relationships import router as relationships_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(health_router)
v1_router.include_router(investigations_router)
v1_router.include_router(documents_router)
v1_router.include_router(chunks_router)
v1_router.include_router(events_router)
v1_router.include_router(entities_router)
v1_router.include_router(cross_investigation_router)
v1_router.include_router(cross_links_router)
v1_router.include_router(graph_router)
v1_router.include_router(query_router)
v1_router.include_router(relationships_router)
v1_router.include_router(system_events_router)
