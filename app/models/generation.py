"""Code generation data models."""

from typing import Literal

from pydantic import BaseModel, Field


class CodeGenOptions(BaseModel):
    """Options for code generation."""

    framework: Literal["nextjs", "react", "vue"] = "nextjs"
    styling: Literal["tailwind", "css", "scss"] = "tailwind"
    include_tests: bool = True
    include_storybook: bool = False
    typescript: bool = True


class GeneratedFile(BaseModel):
    """A generated file."""

    path: str
    content: str
    file_type: Literal["source", "config", "test", "docs", "asset"]
    lines: int = 0

    def __init__(self, **data):
        super().__init__(**data)
        if self.lines == 0:
            self.lines = len(self.content.splitlines())


class GeneratedProject(BaseModel):
    """Complete generated project output."""

    output_directory: str
    files: list[GeneratedFile] = Field(default_factory=list)

    @property
    def file_count(self) -> int:
        """Get total number of files."""
        return len(self.files)

    @property
    def total_lines(self) -> int:
        """Get total lines of code."""
        return sum(f.lines for f in self.files)

    entry_point: str = "src/app/page.tsx"
    build_command: str = "npm run build"
    start_command: str = "npm run dev"

    dependencies: dict[str, str] = Field(default_factory=dict)
    dev_dependencies: dict[str, str] = Field(default_factory=dict)
