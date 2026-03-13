from fastapi import APIRouter

from app.api.v1.documents import router as documents_router
from app.api.v1.entities import router as entities_router
from app.api.v1.events import router as events_router
from app.api.v1.graph import router as graph_router
from app.api.v1.health import router as health_router
from app.api.v1.investigations import router as investigations_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(health_router)
v1_router.include_router(investigations_router)
v1_router.include_router(documents_router)
v1_router.include_router(events_router)
v1_router.include_router(entities_router)
v1_router.include_router(graph_router)
