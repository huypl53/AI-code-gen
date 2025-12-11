"""Health check endpoints."""

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app import __version__
from app.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str
    environment: str
    timestamp: datetime


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check API health status."""
    return HealthResponse(
        status="healthy",
        version=__version__,
        environment=settings.app_env,
        timestamp=datetime.utcnow(),
    )
