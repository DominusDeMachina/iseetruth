from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class StatusEnum(str, Enum):
    healthy = "healthy"
    unhealthy = "unhealthy"
    unavailable = "unavailable"


class OverallStatusEnum(str, Enum):
    healthy = "healthy"
    degraded = "degraded"
    unhealthy = "unhealthy"


class ModelInfo(BaseModel):
    name: str
    available: bool


class ServiceStatus(BaseModel):
    status: StatusEnum
    detail: str
    metadata: Optional[dict] = None


class OllamaStatus(ServiceStatus):
    models_ready: bool
    models: list[ModelInfo]


class HealthResponse(BaseModel):
    status: OverallStatusEnum
    timestamp: datetime
    services: dict[str, ServiceStatus | OllamaStatus]
    warnings: list[str]
