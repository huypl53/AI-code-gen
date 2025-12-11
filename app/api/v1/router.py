"""Main router for API v1."""

from fastapi import APIRouter

from app.api.v1 import health, projects

router = APIRouter(prefix="/v1")

# Include sub-routers
router.include_router(health.router, tags=["health"])
router.include_router(projects.router, prefix="/projects", tags=["projects"])
