"""Embedding service for template matching."""

import hashlib
from functools import lru_cache

from app.models.project_template import ProjectTemplate, TemplateMatch
from app.models.spec import StructuredSpec
from app.utils.logging import get_logger

logger = get_logger("embedding_service")

# Similarity threshold for template matching
DEFAULT_SIMILARITY_THRESHOLD = 0.7

# Common features/keywords to track for embedding
FEATURE_KEYWORDS = [
    # Authentication
    "auth",
    "authentication",
    "login",
    "signup",
    "register",
    "logout",
    "password",
    "session",
    "jwt",
    "oauth",
    # User management
    "user",
    "profile",
    "account",
    "settings",
    "preferences",
    "role",
    "permission",
    # Dashboard & Admin
    "dashboard",
    "admin",
    "analytics",
    "metrics",
    "stats",
    "chart",
    "graph",
    # CRUD operations
    "crud",
    "create",
    "read",
    "update",
    "delete",
    "list",
    "table",
    "grid",
    # Forms & Input
    "form",
    "input",
    "validation",
    "upload",
    "file",
    "image",
    # Navigation & Layout
    "navigation",
    "sidebar",
    "header",
    "footer",
    "menu",
    "breadcrumb",
    # Search & Filter
    "search",
    "filter",
    "sort",
    "pagination",
    "infinite",
    # Notifications
    "notification",
    "alert",
    "toast",
    "email",
    "sms",
    # E-commerce
    "cart",
    "checkout",
    "payment",
    "product",
    "order",
    "invoice",
    # Content
    "blog",
    "post",
    "article",
    "comment",
    "tag",
    "category",
    # API & Data
    "api",
    "rest",
    "graphql",
    "database",
    "fetch",
    "query",
    # Tech stack
    "nextjs",
    "react",
    "vue",
    "tailwind",
    "typescript",
    "zustand",
    "redux",
    "tanstack",
    # Components
    "modal",
    "dialog",
    "dropdown",
    "tabs",
    "accordion",
    "carousel",
    # Features
    "dark",
    "theme",
    "responsive",
    "mobile",
    "i18n",
    "localization",
]


class EmbeddingService:
    """Service for generating and comparing spec embeddings.

    MVP implementation uses keyword-based embeddings.
    For production, integrate with Voyage AI or OpenAI embeddings.
    """

    def __init__(self) -> None:
        self._embedding_cache: dict[str, list[float]] = {}

    def _spec_to_text(self, spec: StructuredSpec) -> str:
        """Convert a StructuredSpec to searchable text."""
        parts = [
            f"Project: {spec.project_name}",
            f"Description: {spec.description}",
            "Features: " + ", ".join(f.name for f in spec.features),
            "Data Models: " + ", ".join(m.name for m in spec.data_models),
            "UI Components: " + ", ".join(c.name for c in spec.ui_components),
            "API Endpoints: " + ", ".join(e.path for e in spec.api_endpoints),
            f"Framework: {spec.tech_recommendations.framework}",
            f"Styling: {spec.tech_recommendations.styling}",
        ]
        return "\n".join(parts)

    def _template_to_text(self, template: ProjectTemplate) -> str:
        """Convert a ProjectTemplate to searchable text."""
        parts = [
            f"Template: {template.name}",
            f"Description: {template.description}",
            "Features: " + ", ".join(template.features),
            f"Framework: {template.tech_stack.framework}",
            f"Styling: {template.tech_stack.styling}",
        ]
        return "\n".join(parts)

    def _compute_text_hash(self, text: str) -> str:
        """Compute a hash of the text for caching."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    async def get_embedding(self, text: str) -> list[float]:
        """Generate embedding for text.

        MVP: Uses keyword presence as embedding dimensions.
        Production: Replace with actual embedding API call.
        """
        text_hash = self._compute_text_hash(text)

        if text_hash in self._embedding_cache:
            return self._embedding_cache[text_hash]

        embedding = self._generate_keyword_embedding(text)
        self._embedding_cache[text_hash] = embedding
        return embedding

    def _generate_keyword_embedding(self, text: str) -> list[float]:
        """Generate embedding based on keyword presence.

        Creates a vector where each dimension represents the presence
        of a feature keyword in the text.
        """
        text_lower = text.lower()
        embedding = [1.0 if kw in text_lower else 0.0 for kw in FEATURE_KEYWORDS]

        # Normalize the vector
        magnitude = sum(x * x for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]

        return embedding

    def cosine_similarity(
        self, embedding1: list[float], embedding2: list[float]
    ) -> float:
        """Compute cosine similarity between two embeddings."""
        if len(embedding1) != len(embedding2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        magnitude1 = sum(x * x for x in embedding1) ** 0.5
        magnitude2 = sum(x * x for x in embedding2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    async def get_spec_embedding(self, spec: StructuredSpec) -> list[float]:
        """Generate embedding for a structured spec."""
        text = self._spec_to_text(spec)
        return await self.get_embedding(text)

    async def get_template_embedding(self, template: ProjectTemplate) -> list[float]:
        """Generate embedding for a project template."""
        text = self._template_to_text(template)
        return await self.get_embedding(text)

    async def match_spec_to_templates(
        self,
        spec: StructuredSpec,
        templates: list[ProjectTemplate],
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ) -> TemplateMatch | None:
        """Find the best matching template for a spec.

        Args:
            spec: The structured specification to match
            templates: Available templates with embeddings
            threshold: Minimum similarity score (0.0 to 1.0)

        Returns:
            Best matching template or None if no match above threshold
        """
        if not templates:
            logger.debug("embedding_service.no_templates")
            return None

        # Generate embedding for the spec
        spec_embedding = await self.get_spec_embedding(spec)

        best_match: TemplateMatch | None = None
        best_score = 0.0

        # Extract spec features for comparison
        spec_features = {f.name.lower() for f in spec.features}

        for template in templates:
            if template.embedding is None:
                continue

            # Compute similarity
            similarity = self.cosine_similarity(spec_embedding, template.embedding)

            # Also check tech stack compatibility
            tech_match = (
                template.tech_stack.framework == spec.tech_recommendations.framework
                and template.tech_stack.styling == spec.tech_recommendations.styling
            )

            # Boost score if tech stack matches
            if tech_match:
                similarity = min(1.0, similarity * 1.15)

            if similarity > best_score and similarity >= threshold:
                best_score = similarity

                template_features = {f.lower() for f in template.features}

                best_match = TemplateMatch(
                    template=template,
                    similarity_score=similarity,
                    matched_features=list(spec_features & template_features),
                    missing_features=list(spec_features - template_features),
                    extra_features=list(template_features - spec_features),
                )

        if best_match:
            logger.info(
                "embedding_service.match_found",
                template_name=best_match.template.name,
                similarity=round(best_match.similarity_score, 3),
                matched_features=len(best_match.matched_features),
                missing_features=len(best_match.missing_features),
            )
        else:
            logger.info(
                "embedding_service.no_match",
                threshold=threshold,
                templates_checked=len(templates),
            )

        return best_match

    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._embedding_cache.clear()


# Singleton instance
_embedding_service: EmbeddingService | None = None


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Get the singleton embedding service."""
    return EmbeddingService()
