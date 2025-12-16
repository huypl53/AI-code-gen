"""Template service for managing project templates."""

import shutil
from functools import lru_cache
from pathlib import Path
from typing import Literal
from uuid import UUID

from app.core.template_repository import TemplateRepository, get_template_repository
from app.models.generation import GeneratedFile
from app.models.project_template import (
    ProjectTemplate,
    TechStack,
    TemplateMatch,
)
from app.models.spec import StructuredSpec
from app.services.embedding_service import (
    DEFAULT_SIMILARITY_THRESHOLD,
    EmbeddingService,
    get_embedding_service,
)
from app.utils.logging import get_logger

logger = get_logger("template_service")

# Base directory for template storage
TEMPLATES_DIR = Path(__file__).parent.parent / "generators" / "templates"


class TemplateService:
    """Service for template management and matching."""

    def __init__(
        self,
        repository: TemplateRepository | None = None,
        embedding_service: EmbeddingService | None = None,
        templates_dir: Path | None = None,
    ):
        self.repository = repository or get_template_repository()
        self.embedding_service = embedding_service or get_embedding_service()
        self.templates_dir = templates_dir or TEMPLATES_DIR
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    async def create_template_from_project(
        self,
        name: str,
        description: str,
        source_dir: Path,
        features: list[str],
        tech_stack: TechStack | None = None,
    ) -> ProjectTemplate:
        """Create a new template from an existing project directory.

        Args:
            name: Unique template name
            description: Template description
            source_dir: Path to the source project
            features: List of feature tags
            tech_stack: Technology stack configuration

        Returns:
            Created ProjectTemplate

        Raises:
            ValueError: If template name already exists or source not found
        """
        # Validate source directory
        if not source_dir.exists():
            raise ValueError(f"Source directory not found: {source_dir}")

        # Check if template already exists
        existing = await self.repository.get_by_name(name)
        if existing:
            raise ValueError(f"Template '{name}' already exists")

        # Create template directory
        template_path = self.templates_dir / name
        if template_path.exists():
            raise ValueError(f"Template directory already exists: {template_path}")

        # Copy project files (excluding node_modules, .git, etc.)
        shutil.copytree(
            source_dir,
            template_path,
            ignore=shutil.ignore_patterns(
                "node_modules",
                ".git",
                ".next",
                "dist",
                "build",
                "__pycache__",
                "*.pyc",
                ".env",
                ".env.local",
            ),
        )

        # Count files and lines
        file_count, total_lines = self._count_files_and_lines(template_path)

        # Create template record
        template = ProjectTemplate(
            name=name,
            description=description,
            project_path=name,  # Relative to templates_dir
            tech_stack=tech_stack or TechStack(),
            features=features,
            file_count=file_count,
            total_lines=total_lines,
        )

        # Generate embedding
        embedding = await self.embedding_service.get_template_embedding(template)
        template.embedding = embedding

        # Save to database
        await self.repository.create(template)

        logger.info(
            "template_service.created",
            name=name,
            file_count=file_count,
            total_lines=total_lines,
        )

        return template

    def _count_files_and_lines(self, directory: Path) -> tuple[int, int]:
        """Count files and total lines in a directory."""
        file_count = 0
        total_lines = 0

        for file_path in directory.rglob("*"):
            if file_path.is_file():
                # Skip binary files and hidden files
                if file_path.name.startswith("."):
                    continue

                file_count += 1
                try:
                    content = file_path.read_text(encoding="utf-8")
                    total_lines += len(content.splitlines())
                except (UnicodeDecodeError, PermissionError):
                    pass  # Skip binary/unreadable files

        return file_count, total_lines

    async def find_matching_template(
        self,
        spec: StructuredSpec,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ) -> TemplateMatch | None:
        """Find the best matching template for a specification.

        Args:
            spec: The structured specification
            threshold: Minimum similarity score (0.0 to 1.0)

        Returns:
            Best match or None if no suitable template found
        """
        templates = await self.repository.get_all_with_embeddings()

        if not templates:
            logger.info("template_service.no_templates_available")
            return None

        return await self.embedding_service.match_spec_to_templates(
            spec=spec,
            templates=templates,
            threshold=threshold,
        )

    async def copy_template_to_directory(
        self,
        template: ProjectTemplate,
        output_dir: Path,
    ) -> list[GeneratedFile]:
        """Copy a template to an output directory.

        Args:
            template: The template to copy
            output_dir: Destination directory

        Returns:
            List of copied files as GeneratedFile objects

        Raises:
            ValueError: If template source not found
        """
        source_dir = self.templates_dir / template.project_path

        if not source_dir.exists():
            raise ValueError(f"Template source not found: {source_dir}")

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Copy files (excluding node_modules if it exists)
        shutil.copytree(
            source_dir,
            output_dir,
            ignore=shutil.ignore_patterns("node_modules", ".git", ".next"),
            dirs_exist_ok=True,
        )

        # Increment usage count
        await self.repository.increment_usage(template.id)

        # Scan copied files
        files = self._scan_directory_files(output_dir)

        logger.info(
            "template_service.copied",
            template=template.name,
            output_dir=str(output_dir),
            files_count=len(files),
        )

        return files

    def _scan_directory_files(self, directory: Path) -> list[GeneratedFile]:
        """Scan a directory and return GeneratedFile objects."""
        files: list[GeneratedFile] = []

        for file_path in directory.rglob("*"):
            if not file_path.is_file():
                continue

            relative_path = file_path.relative_to(directory)
            str_path = str(relative_path)

            # Skip node_modules and hidden files
            if "node_modules" in str_path or file_path.name.startswith("."):
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
                file_type = self._determine_file_type(str_path)
                files.append(
                    GeneratedFile(
                        path=str_path,
                        content=content,
                        file_type=file_type,
                    )
                )
            except (UnicodeDecodeError, PermissionError):
                pass  # Skip binary/unreadable files

        return files

    def _determine_file_type(
        self, path: str
    ) -> Literal["source", "config", "test", "docs", "asset"]:
        """Determine file type from path."""
        path_lower = path.lower()

        if "test" in path_lower or "spec" in path_lower:
            return "test"
        elif path_lower.endswith((".md", ".txt", ".rst")):
            return "docs"
        elif path_lower.endswith((".json", ".yaml", ".yml", ".toml", ".config.js", ".config.ts")):
            return "config"
        elif path_lower.endswith((".png", ".jpg", ".jpeg", ".svg", ".ico", ".gif", ".webp")):
            return "asset"
        else:
            return "source"

    async def list_templates(self) -> list[ProjectTemplate]:
        """List all available templates."""
        return await self.repository.list_all()

    async def get_template(self, template_id: UUID) -> ProjectTemplate | None:
        """Get a template by ID."""
        return await self.repository.get_by_id(template_id)

    async def get_template_by_name(self, name: str) -> ProjectTemplate | None:
        """Get a template by name."""
        return await self.repository.get_by_name(name)

    async def delete_template(self, template_id: UUID) -> bool:
        """Delete a template and its files.

        Args:
            template_id: ID of the template to delete

        Returns:
            True if template was deleted, False if not found
        """
        template = await self.repository.get_by_id(template_id)
        if not template:
            return False

        # Delete files
        template_path = self.templates_dir / template.project_path
        if template_path.exists():
            shutil.rmtree(template_path)
            logger.info(
                "template_service.files_deleted",
                template_path=str(template_path),
            )

        # Delete from database
        deleted = await self.repository.delete(template_id)

        if deleted:
            logger.info(
                "template_service.deleted",
                template_id=str(template_id),
                name=template.name,
            )

        return deleted

    async def refresh_template_embedding(self, template_id: UUID) -> bool:
        """Refresh the embedding for a template.

        Args:
            template_id: ID of the template

        Returns:
            True if embedding was updated, False if template not found
        """
        template = await self.repository.get_by_id(template_id)
        if not template:
            return False

        embedding = await self.embedding_service.get_template_embedding(template)
        await self.repository.update_embedding(template_id, embedding)

        logger.info(
            "template_service.embedding_refreshed",
            template_id=str(template_id),
        )

        return True


# Singleton instance
_template_service: TemplateService | None = None


@lru_cache(maxsize=1)
def get_template_service() -> TemplateService:
    """Get the singleton template service."""
    return TemplateService()
