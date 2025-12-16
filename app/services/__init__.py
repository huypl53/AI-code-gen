"""Services for the app-agent application."""

from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.template_service import TemplateService, get_template_service

__all__ = [
    "EmbeddingService",
    "get_embedding_service",
    "TemplateService",
    "get_template_service",
]
