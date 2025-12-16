"""Main router for API v1."""

from fastapi import APIRouter

from app.api.v1 import health, project_templates, projects, templates

router = APIRouter(prefix="/v1")

# Include sub-routers
router.include_router(health.router, tags=["health"])
router.include_router(projects.router, prefix="/projects", tags=["projects"])
router.include_router(templates.router, prefix="/templates", tags=["templates"])
router.include_router(
    project_templates.router,
    prefix="/project-templates",
    tags=["project-templates"],
)
