"""SQLite repository for project templates."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Iterator
from uuid import UUID

from app.config import settings
from app.models.project_template import ProjectTemplate, TechStack
from app.utils.logging import get_logger

logger = get_logger("template_repository")

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve_db_path(db_path: str | Path) -> Path:
    """Resolve database path relative to project root when not absolute."""
    path = Path(db_path)
    return path if path.is_absolute() else PROJECT_ROOT / path


# Database file path
DB_PATH = _resolve_db_path(settings.template_db_path)


class TemplateRepository:
    """Repository for managing project templates in SQLite."""

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = _resolve_db_path(db_path or DB_PATH)
        self._ensure_db_exists()

    def _ensure_db_exists(self) -> None:
        """Create database and tables if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_templates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    project_path TEXT NOT NULL UNIQUE,
                    tech_stack TEXT NOT NULL,
                    features TEXT NOT NULL,
                    embedding TEXT,
                    usage_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    source_spec_hash TEXT,
                    file_count INTEGER DEFAULT 0,
                    total_lines INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_templates_name
                ON project_templates(name)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_templates_usage
                ON project_templates(usage_count DESC)
            """)
            conn.commit()

        logger.debug("template_repository.initialized", db_path=str(self.db_path))

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _row_to_template(self, row: sqlite3.Row) -> ProjectTemplate:
        """Convert a database row to a ProjectTemplate."""
        return ProjectTemplate(
            id=UUID(row["id"]),
            name=row["name"],
            description=row["description"] or "",
            project_path=row["project_path"],
            tech_stack=TechStack(**json.loads(row["tech_stack"])),
            features=json.loads(row["features"]),
            embedding=json.loads(row["embedding"]) if row["embedding"] else None,
            usage_count=row["usage_count"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            source_spec_hash=row["source_spec_hash"],
            file_count=row["file_count"],
            total_lines=row["total_lines"],
        )

    async def create(self, template: ProjectTemplate) -> ProjectTemplate:
        """Insert a new template into the database."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO project_templates
                (id, name, description, project_path, tech_stack, features,
                 embedding, usage_count, created_at, updated_at,
                 source_spec_hash, file_count, total_lines)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(template.id),
                    template.name,
                    template.description,
                    template.project_path,
                    json.dumps(template.tech_stack.model_dump()),
                    json.dumps(template.features),
                    json.dumps(template.embedding) if template.embedding else None,
                    template.usage_count,
                    template.created_at.isoformat(),
                    template.updated_at.isoformat(),
                    template.source_spec_hash,
                    template.file_count,
                    template.total_lines,
                ),
            )
            conn.commit()

        logger.info(
            "template_repository.created",
            template_id=str(template.id),
            name=template.name,
        )
        return template

    async def get_by_id(self, template_id: UUID) -> ProjectTemplate | None:
        """Get a template by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM project_templates WHERE id = ?",
                (str(template_id),),
            ).fetchone()

        return self._row_to_template(row) if row else None

    async def get_by_name(self, name: str) -> ProjectTemplate | None:
        """Get a template by name."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM project_templates WHERE name = ?",
                (name,),
            ).fetchone()

        return self._row_to_template(row) if row else None

    async def list_all(self) -> list[ProjectTemplate]:
        """List all templates ordered by usage count."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM project_templates ORDER BY usage_count DESC"
            ).fetchall()

        return [self._row_to_template(row) for row in rows]

    async def get_all_with_embeddings(self) -> list[ProjectTemplate]:
        """Get all templates that have embeddings computed."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM project_templates WHERE embedding IS NOT NULL"
            ).fetchall()

        return [self._row_to_template(row) for row in rows]

    async def update_embedding(
        self, template_id: UUID, embedding: list[float]
    ) -> None:
        """Update the embedding vector for a template."""
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE project_templates
                SET embedding = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    json.dumps(embedding),
                    datetime.utcnow().isoformat(),
                    str(template_id),
                ),
            )
            conn.commit()

        logger.debug(
            "template_repository.embedding_updated",
            template_id=str(template_id),
        )

    async def increment_usage(self, template_id: UUID) -> None:
        """Increment the usage count for a template."""
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE project_templates
                SET usage_count = usage_count + 1, updated_at = ?
                WHERE id = ?
                """,
                (datetime.utcnow().isoformat(), str(template_id)),
            )
            conn.commit()

        logger.debug(
            "template_repository.usage_incremented",
            template_id=str(template_id),
        )

    async def update(self, template: ProjectTemplate) -> ProjectTemplate:
        """Update an existing template."""
        template.updated_at = datetime.utcnow()

        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE project_templates
                SET name = ?, description = ?, project_path = ?, tech_stack = ?,
                    features = ?, embedding = ?, usage_count = ?, updated_at = ?,
                    source_spec_hash = ?, file_count = ?, total_lines = ?
                WHERE id = ?
                """,
                (
                    template.name,
                    template.description,
                    template.project_path,
                    json.dumps(template.tech_stack.model_dump()),
                    json.dumps(template.features),
                    json.dumps(template.embedding) if template.embedding else None,
                    template.usage_count,
                    template.updated_at.isoformat(),
                    template.source_spec_hash,
                    template.file_count,
                    template.total_lines,
                    str(template.id),
                ),
            )
            conn.commit()

        logger.info(
            "template_repository.updated",
            template_id=str(template.id),
        )
        return template

    async def delete(self, template_id: UUID) -> bool:
        """Delete a template by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM project_templates WHERE id = ?",
                (str(template_id),),
            )
            conn.commit()
            deleted = cursor.rowcount > 0

        if deleted:
            logger.info(
                "template_repository.deleted",
                template_id=str(template_id),
            )
        return deleted


# Singleton instance
_repository: TemplateRepository | None = None


@lru_cache(maxsize=1)
def get_template_repository() -> TemplateRepository:
    """Get the singleton template repository."""
    return TemplateRepository()
