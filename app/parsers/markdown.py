"""Markdown specification parser.

Parses markdown specifications into structured data for further processing.
"""

import re
from dataclasses import dataclass, field

from app.models.spec import (
    APIEndpoint,
    ComponentProp,
    DataModel,
    Feature,
    ModelField,
    UIComponent,
)


@dataclass
class ParsedMarkdown:
    """Result of parsing a markdown specification."""

    title: str = ""
    description: str = ""
    features: list[Feature] = field(default_factory=list)
    data_models: list[DataModel] = field(default_factory=list)
    api_endpoints: list[APIEndpoint] = field(default_factory=list)
    ui_components: list[UIComponent] = field(default_factory=list)
    raw_sections: dict[str, str] = field(default_factory=dict)


class MarkdownParser:
    """Parser for markdown specifications."""

    def parse(self, content: str) -> ParsedMarkdown:
        """Parse markdown content into structured data."""
        result = ParsedMarkdown()

        # Extract title (first H1)
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if title_match:
            result.title = title_match.group(1).strip()

        # Split into sections by H2 headers
        sections = self._split_sections(content)
        result.raw_sections = sections

        # Parse description
        if "description" in sections:
            result.description = sections["description"].strip()

        # Parse features
        if "features" in sections:
            result.features = self._parse_features(sections["features"])

        # Parse data models
        if "data models" in sections:
            result.data_models = self._parse_data_models(sections["data models"])

        # Parse API endpoints
        if "api endpoints" in sections:
            result.api_endpoints = self._parse_api_endpoints(sections["api endpoints"])
        elif "api" in sections:
            result.api_endpoints = self._parse_api_endpoints(sections["api"])

        # Parse UI components
        if "ui components" in sections:
            result.ui_components = self._parse_ui_components(sections["ui components"])
        elif "components" in sections:
            result.ui_components = self._parse_ui_components(sections["components"])

        return result

    def _split_sections(self, content: str) -> dict[str, str]:
        """Split content into sections by H2 headers."""
        sections: dict[str, str] = {}

        # Find all H2 headers and their positions
        pattern = r"^##\s+(.+)$"
        matches = list(re.finditer(pattern, content, re.MULTILINE))

        for i, match in enumerate(matches):
            section_name = match.group(1).strip().lower()
            start = match.end()

            # Find end of section (next H2 or end of content)
            if i + 1 < len(matches):
                end = matches[i + 1].start()
            else:
                end = len(content)

            sections[section_name] = content[start:end].strip()

        return sections

    def _parse_features(self, content: str) -> list[Feature]:
        """Parse features from markdown content."""
        features: list[Feature] = []

        # Try to parse H3 subsections first
        h3_sections = self._split_h3_sections(content)

        if h3_sections:
            # Features organized by subsections
            for section_name, section_content in h3_sections.items():
                section_features = self._extract_list_items(section_content)
                for i, item in enumerate(section_features):
                    name, description = self._parse_feature_item(item)
                    features.append(
                        Feature(
                            id=f"f_{len(features) + 1}",
                            name=name,
                            description=description,
                            priority="must" if "core" in section_name.lower() else "should",
                        )
                    )
        else:
            # Simple list of features
            items = self._extract_list_items(content)
            for i, item in enumerate(items):
                name, description = self._parse_feature_item(item)
                features.append(
                    Feature(
                        id=f"f_{i + 1}",
                        name=name,
                        description=description,
                    )
                )

        return features

    def _parse_feature_item(self, item: str) -> tuple[str, str]:
        """Parse a feature list item into name and description."""
        # Handle bold name: **Name**: Description
        bold_match = re.match(r"\*\*(.+?)\*\*[:\s]*(.*)$", item)
        if bold_match:
            return bold_match.group(1).strip(), bold_match.group(2).strip()

        # Handle colon separator: Name: Description
        if ":" in item:
            parts = item.split(":", 1)
            return parts[0].strip(), parts[1].strip() if len(parts) > 1 else ""

        # Just the name
        return item.strip(), ""

    def _parse_data_models(self, content: str) -> list[DataModel]:
        """Parse data models from markdown content."""
        models: list[DataModel] = []

        # Split by H3 headers (each model is an H3)
        h3_sections = self._split_h3_sections(content)

        for model_name, model_content in h3_sections.items():
            fields = self._parse_model_fields(model_content)
            models.append(
                DataModel(
                    name=model_name,
                    description=f"The {model_name} entity",
                    fields=fields,
                )
            )

        return models

    def _parse_model_fields(self, content: str) -> list[ModelField]:
        """Parse model fields from content."""
        fields: list[ModelField] = []

        # Try table format first
        table_fields = self._parse_table(content)
        if table_fields:
            for row in table_fields:
                if len(row) >= 2:
                    name = row[0].strip()
                    field_type = row[1].strip() if len(row) > 1 else "string"
                    required = "yes" in row[2].lower() if len(row) > 2 else True
                    description = row[3].strip() if len(row) > 3 else ""

                    fields.append(
                        ModelField(
                            name=name,
                            type=self._normalize_type(field_type),
                            required=required,
                            description=description if description else None,
                        )
                    )
            return fields

        # Fall back to list format: - field_name: type (description)
        items = self._extract_list_items(content)
        for item in items:
            match = re.match(r"(\w+)[:\s]+(\w+)(?:\s*\((.+)\))?", item)
            if match:
                name = match.group(1)
                field_type = match.group(2)
                description = match.group(3) if match.group(3) else ""

                required = "required" in description.lower() or "optional" not in description.lower()

                fields.append(
                    ModelField(
                        name=name,
                        type=self._normalize_type(field_type),
                        required=required,
                        description=description if description else None,
                    )
                )

        return fields

    def _normalize_type(self, type_str: str) -> str:
        """Normalize type strings."""
        type_str = type_str.lower().strip()
        type_map = {
            "uuid": "uuid",
            "string": "string",
            "str": "string",
            "text": "string",
            "varchar": "string",
            "int": "number",
            "integer": "number",
            "float": "number",
            "decimal": "number",
            "number": "number",
            "bool": "boolean",
            "boolean": "boolean",
            "date": "date",
            "datetime": "datetime",
            "timestamp": "datetime",
            "json": "json",
            "object": "json",
            "array": "array",
            "list": "array",
            "enum": "enum",
        }
        return type_map.get(type_str, type_str)

    def _parse_api_endpoints(self, content: str) -> list[APIEndpoint]:
        """Parse API endpoints from markdown content."""
        endpoints: list[APIEndpoint] = []

        # Look for patterns like:
        # - GET /api/tasks - Description
        # - **GET** `/api/tasks` - Description
        # ### List Tasks
        # - **GET** `/api/tasks`

        # First try H3 sections
        h3_sections = self._split_h3_sections(content)

        for endpoint_name, endpoint_content in h3_sections.items():
            # Look for method and path
            method_match = re.search(
                r"\*?\*?(GET|POST|PUT|PATCH|DELETE)\*?\*?\s*[`\"]?(/[\w/{}\-]+)[`\"]?",
                endpoint_content,
                re.IGNORECASE,
            )
            if method_match:
                method = method_match.group(1).upper()
                path = method_match.group(2)

                endpoints.append(
                    APIEndpoint(
                        method=method,  # type: ignore
                        path=path,
                        description=endpoint_name,
                    )
                )

        # Also parse list items
        items = self._extract_list_items(content)
        for item in items:
            match = re.search(
                r"\*?\*?(GET|POST|PUT|PATCH|DELETE)\*?\*?\s*[`\"]?(/[\w/{}\-]+)[`\"]?\s*[-–—]?\s*(.*)$",
                item,
                re.IGNORECASE,
            )
            if match:
                method = match.group(1).upper()
                path = match.group(2)
                description = match.group(3).strip()

                # Avoid duplicates
                existing = [e for e in endpoints if e.method == method and e.path == path]
                if not existing:
                    endpoints.append(
                        APIEndpoint(
                            method=method,  # type: ignore
                            path=path,
                            description=description or f"{method} {path}",
                        )
                    )

        return endpoints

    def _parse_ui_components(self, content: str) -> list[UIComponent]:
        """Parse UI components from markdown content."""
        components: list[UIComponent] = []

        # Split by H3 sections
        h3_sections = self._split_h3_sections(content)

        for section_name, section_content in h3_sections.items():
            comp_type = "component"
            if "page" in section_name.lower():
                comp_type = "page"
            elif "layout" in section_name.lower():
                comp_type = "layout"

            # Parse component list items
            items = self._extract_list_items(section_content)
            for item in items:
                name, description = self._parse_feature_item(item)
                if name:
                    components.append(
                        UIComponent(
                            name=name,
                            type=comp_type,  # type: ignore
                            description=description or f"{name} component",
                        )
                    )

        return components

    def _split_h3_sections(self, content: str) -> dict[str, str]:
        """Split content into sections by H3 headers."""
        sections: dict[str, str] = {}

        pattern = r"^###\s+(.+)$"
        matches = list(re.finditer(pattern, content, re.MULTILINE))

        for i, match in enumerate(matches):
            section_name = match.group(1).strip()
            start = match.end()

            if i + 1 < len(matches):
                end = matches[i + 1].start()
            else:
                end = len(content)

            sections[section_name] = content[start:end].strip()

        return sections

    def _extract_list_items(self, content: str) -> list[str]:
        """Extract list items from content."""
        items: list[str] = []
        pattern = r"^[\s]*[-*]\s+(.+)$"

        for match in re.finditer(pattern, content, re.MULTILINE):
            items.append(match.group(1).strip())

        return items

    def _parse_table(self, content: str) -> list[list[str]]:
        """Parse a markdown table into rows."""
        rows: list[list[str]] = []

        # Find table rows (lines with | separators)
        table_pattern = r"^\|(.+)\|$"
        matches = list(re.finditer(table_pattern, content, re.MULTILINE))

        for i, match in enumerate(matches):
            row_content = match.group(1)

            # Skip separator rows (----)
            if re.match(r"^[\s\-:|]+$", row_content):
                continue

            # Skip header row (first row)
            if i == 0:
                continue

            cells = [cell.strip() for cell in row_content.split("|")]
            rows.append(cells)

        return rows


def parse_markdown_spec(content: str) -> ParsedMarkdown:
    """Parse a markdown specification string."""
    parser = MarkdownParser()
    return parser.parse(content)
