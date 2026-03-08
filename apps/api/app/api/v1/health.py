from fastapi import APIRouter

from app.schemas.health import HealthResponse
from app.services.health import HealthService

router = APIRouter()


@router.get("/health/", response_model=HealthResponse)
async def health_check():
    service = HealthService()
    return await service.get_health()
